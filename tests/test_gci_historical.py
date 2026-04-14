"""
Tests for calculate_gci_historical.py

Covers:
- Importing compute_game_metrics from calculate_gci
- compute_game_metrics basic behavior and edge cases
- load_season_games: derives game results from WP replay files
- compute_season_gci: processes one season end-to-end
- compute_league_trends: league-wide aggregates across seasons
- compute_team_trends: per-team trend arrays
- find_historical_superlatives: all-time records
"""

import json
import os
import sys
import tempfile

import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculate_gci import compute_game_metrics, aggregate_team_profiles, compute_gci_ratings
import calculate_gci_historical as hist


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_timeline(wp_values, period=4):
    """Build a minimal timeline list from a sequence of WP values."""
    n = len(wp_values)
    entries = []
    for i, w in enumerate(wp_values):
        s = int(2400 * (1 - i / max(n - 1, 1)))
        entries.append({'e': 2400 - s, 's': s, 'a': i, 'b': i + 1, 'w': w, 'p': period, 'd': ''})
    # Ensure the last entry has s=0
    entries[-1]['s'] = 0
    return entries


def make_wp_file(ta, tb, timeline):
    """Return a dict matching the WP replay JSON schema."""
    return {'ta': ta, 'tb': tb, 'timeline': timeline}


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------

class TestImports:
    def test_compute_game_metrics_importable(self):
        assert callable(compute_game_metrics)

    def test_aggregate_team_profiles_importable(self):
        assert callable(aggregate_team_profiles)

    def test_compute_gci_ratings_importable(self):
        assert callable(compute_gci_ratings)

    def test_hist_module_importable(self):
        assert hasattr(hist, 'load_season_games')
        assert hasattr(hist, 'compute_season_gci')
        assert hasattr(hist, 'compute_league_trends')
        assert hasattr(hist, 'compute_team_trends')
        assert hasattr(hist, 'compute_era_breakdowns')
        assert hasattr(hist, 'find_historical_superlatives')
        assert hasattr(hist, 'build_season_leaderboards')


# ---------------------------------------------------------------------------
# 2. compute_game_metrics behaviour
# ---------------------------------------------------------------------------

class TestComputeGameMetrics:
    def _home_win_timeline(self):
        """Simple timeline where home team leads throughout and wins."""
        wps = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0]
        return make_timeline(wps)

    def _away_win_timeline(self):
        """Simple timeline where away team leads throughout and wins."""
        wps = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.0]
        return make_timeline(wps)

    def test_returns_none_for_empty_timeline(self):
        assert compute_game_metrics([], True) is None

    def test_returns_none_for_short_timeline(self):
        timeline = [{'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''}]
        assert compute_game_metrics(timeline, True) is None
        timeline2 = timeline * 2
        assert compute_game_metrics(timeline2, True) is None

    def test_returns_dict_with_required_keys(self):
        timeline = self._home_win_timeline()
        result = compute_game_metrics(timeline, True)
        assert result is not None
        required = {
            'dominance', 'control_home', 'control_away', 'drama',
            'comeback', 'crunch_home', 'crunch_away', 'killer_home', 'killer_away'
        }
        assert required == set(result.keys())

    def test_dominance_positive_for_home_dominated_game(self):
        """When home WP is consistently > 0.5, dominance should be positive."""
        timeline = self._home_win_timeline()
        result = compute_game_metrics(timeline, True)
        assert result['dominance'] > 0

    def test_dominance_negative_for_away_dominated_game(self):
        """When home WP is consistently < 0.5, dominance should be negative."""
        timeline = self._away_win_timeline()
        result = compute_game_metrics(timeline, False)
        assert result['dominance'] < 0

    def test_control_home_between_0_and_1(self):
        timeline = self._home_win_timeline()
        result = compute_game_metrics(timeline, True)
        assert 0.0 <= result['control_home'] <= 1.0

    def test_control_away_between_0_and_1(self):
        timeline = self._away_win_timeline()
        result = compute_game_metrics(timeline, False)
        assert 0.0 <= result['control_away'] <= 1.0

    def test_drama_non_negative(self):
        timeline = self._home_win_timeline()
        result = compute_game_metrics(timeline, True)
        assert result['drama'] >= 0

    def test_drama_higher_for_volatile_game(self):
        """A game with big WP swings should have higher drama than a monotone one."""
        monotone = make_timeline([0.6, 0.65, 0.7, 0.72, 0.75, 0.78, 0.80, 1.0])
        volatile = make_timeline([0.5, 0.9, 0.1, 0.9, 0.1, 0.8, 0.2, 1.0])
        m_mono = compute_game_metrics(monotone, True)
        m_vol = compute_game_metrics(volatile, True)
        assert m_vol['drama'] > m_mono['drama']

    def test_comeback_home_win_from_low_probability(self):
        """Home team winning after dipping to 0.1 WP — comeback should be large."""
        # Home dips to 0.1 then recovers to win
        wps = [0.5, 0.3, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        timeline = make_timeline(wps)
        result = compute_game_metrics(timeline, winner_is_home=True)
        # comeback = 1.0 - min(WP) = 1.0 - 0.1 = 0.9
        assert result['comeback'] == pytest.approx(0.9, abs=0.01)

    def test_comeback_away_win_from_high_opponent_probability(self):
        """Away team winning when home WP peaked at 0.9 — comeback should be ~0.9."""
        wps = [0.5, 0.7, 0.9, 0.7, 0.5, 0.3, 0.1, 0.0]
        timeline = make_timeline(wps)
        result = compute_game_metrics(timeline, winner_is_home=False)
        # comeback for away = max(wp_values) = 0.9
        assert result['comeback'] == pytest.approx(0.9, abs=0.01)

    def test_crunch_home_zero_when_no_crunch_plays(self):
        """If all plays have s > 300, crunch values should be 0."""
        timeline = [
            {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
            {'e': 600, 's': 1800, 'a': 2, 'b': 0, 'w': 0.6, 'p': 2, 'd': ''},
            {'e': 1200, 's': 1200, 'a': 4, 'b': 0, 'w': 0.7, 'p': 3, 'd': ''},
            {'e': 1800, 's': 600, 'a': 6, 'b': 0, 'w': 0.8, 'p': 4, 'd': ''},
        ]
        result = compute_game_metrics(timeline, True)
        assert result['crunch_home'] == 0.0
        assert result['crunch_away'] == 0.0

    def test_crunch_home_and_away_are_negatives(self):
        """crunch_home and crunch_away should sum to 0 (one is the negative of the other)."""
        wps = [0.5, 0.55, 0.6, 0.65, 0.5, 0.4, 0.3, 0.8, 1.0]
        timeline = make_timeline(wps)
        result = compute_game_metrics(timeline, True)
        assert result['crunch_home'] == pytest.approx(-result['crunch_away'], abs=1e-6)

    def test_all_values_are_rounded_floats(self):
        timeline = self._home_win_timeline()
        result = compute_game_metrics(timeline, True)
        for key, val in result.items():
            assert isinstance(val, float), f"{key} should be float"


# ---------------------------------------------------------------------------
# 3. load_season_games
# ---------------------------------------------------------------------------

class TestLoadSeasonGames:
    def _write_wp_file(self, directory, gamecode, ta, tb, timeline):
        path = os.path.join(directory, f"{gamecode}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'ta': ta, 'tb': tb, 'timeline': timeline}, f)

    def test_returns_tuple_of_two_dicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tl = make_timeline([0.5, 0.6, 0.7, 1.0])
            self._write_wp_file(tmpdir, '1', 'OLY', 'BAR', tl)
            games, timelines = hist.load_season_games(tmpdir)
            assert isinstance(games, dict)
            assert isinstance(timelines, dict)

    def test_single_game_home_win(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Home (OLY) wins: final w=1.0, final a>b (3 entries to pass minimum)
            tl = [
                {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                {'e': 1200, 's': 1200, 'a': 40, 'b': 35, 'w': 0.6, 'p': 3, 'd': ''},
                {'e': 2400, 's': 0, 'a': 80, 'b': 70, 'w': 1.0, 'p': 4, 'd': 'Final Buzzer'},
            ]
            self._write_wp_file(tmpdir, '42', 'OLY', 'BAR', tl)
            games, timelines = hist.load_season_games(tmpdir)
            assert '42' in games
            g = games['42']
            assert g['home'] == 'OLY'
            assert g['away'] == 'BAR'
            assert g['home_score'] == 80
            assert g['away_score'] == 70
            assert g['winner'] == 'OLY'

    def test_single_game_away_win(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tl = [
                {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                {'e': 1200, 's': 1200, 'a': 30, 'b': 38, 'w': 0.4, 'p': 3, 'd': ''},
                {'e': 2400, 's': 0, 'a': 65, 'b': 75, 'w': 0.0, 'p': 4, 'd': 'Final Buzzer'},
            ]
            self._write_wp_file(tmpdir, '7', 'MAD', 'CSK', tl)
            games, timelines = hist.load_season_games(tmpdir)
            g = games['7']
            assert g['winner'] == 'CSK'
            assert g['home_score'] == 65
            assert g['away_score'] == 75

    def test_timelines_contains_full_timeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tl = [
                {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                {'e': 1200, 's': 1200, 'a': 40, 'b': 38, 'w': 0.55, 'p': 3, 'd': ''},
                {'e': 2400, 's': 0, 'a': 80, 'b': 70, 'w': 1.0, 'p': 4, 'd': 'Final Buzzer'},
            ]
            self._write_wp_file(tmpdir, '3', 'AXA', 'UNI', tl)
            games, timelines = hist.load_season_games(tmpdir)
            assert '3' in timelines
            assert len(timelines['3']) == 3

    def test_empty_directory_returns_empty_dicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            games, timelines = hist.load_season_games(tmpdir)
            assert games == {}
            assert timelines == {}

    def test_nonexistent_directory_returns_empty_dicts(self):
        games, timelines = hist.load_season_games('/nonexistent/path/xyz')
        assert games == {}
        assert timelines == {}

    def test_skips_files_with_short_timeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only 1 entry — too short
            short_tl = [{'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''}]
            self._write_wp_file(tmpdir, '99', 'OLY', 'BAR', short_tl)
            games, timelines = hist.load_season_games(tmpdir)
            assert '99' not in games

    def test_multiple_games_all_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(1, 6):
                tl = [
                    {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                    {'e': 1200, 's': 1200, 'a': 40, 'b': 35, 'w': 0.6, 'p': 3, 'd': ''},
                    {'e': 2400, 's': 0, 'a': 80, 'b': 70, 'w': 1.0, 'p': 4, 'd': 'Final Buzzer'},
                ]
                self._write_wp_file(tmpdir, str(i), f'T{i}', f'T{i+10}', tl)
            games, timelines = hist.load_season_games(tmpdir)
            assert len(games) == 5

    def test_winner_determined_by_final_wp_not_scores_alone(self):
        """Winner should come from final WP value (w→1.0 = home, w→0.0 = away)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Final w=1.0 means home wins (regardless of 'a' vs 'b' comparison)
            tl = [
                {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                {'e': 1200, 's': 1200, 'a': 40, 'b': 40, 'w': 0.5, 'p': 3, 'd': ''},
                {'e': 2400, 's': 0, 'a': 80, 'b': 79, 'w': 1.0, 'p': 4, 'd': 'Final Buzzer'},
            ]
            self._write_wp_file(tmpdir, '5', 'HOM', 'AWY', tl)
            games, _ = hist.load_season_games(tmpdir)
            assert games['5']['winner'] == 'HOM'


# ---------------------------------------------------------------------------
# 4. compute_season_gci
# ---------------------------------------------------------------------------

class TestComputeSeasonGci:
    def _make_season_data(self, n_games=4):
        """Build minimal games/timelines dicts for n_games games."""
        teams = ['OLY', 'BAR', 'MAD', 'CSK']
        games = {}
        timelines = {}
        for i in range(n_games):
            gc = str(i + 1)
            home = teams[i % len(teams)]
            away = teams[(i + 1) % len(teams)]
            tl = [
                {'e': 0, 's': 2400, 'a': 0, 'b': 0, 'w': 0.5, 'p': 1, 'd': ''},
                {'e': 600, 's': 1800, 'a': 20, 'b': 18, 'w': 0.55, 'p': 2, 'd': ''},
                {'e': 1200, 's': 1200, 'a': 40, 'b': 36, 'w': 0.6, 'p': 3, 'd': ''},
                {'e': 1800, 's': 600, 'a': 60, 'b': 54, 'w': 0.7, 'p': 4, 'd': ''},
                {'e': 2100, 's': 300, 'a': 70, 'b': 60, 'w': 0.8, 'p': 4, 'd': ''},
                {'e': 2400, 's': 0, 'a': 85, 'b': 70, 'w': 1.0, 'p': 4, 'd': 'Final Buzzer'},
            ]
            games[gc] = {
                'home': home, 'away': away,
                'home_score': 85, 'away_score': 70,
                'winner': home,
            }
            timelines[gc] = tl
        return games, timelines

    def test_returns_dict_with_required_keys(self):
        games, timelines = self._make_season_data()
        result = hist.compute_season_gci(games, timelines)
        assert isinstance(result, dict)
        for key in ('gci_ratings', 'components', 'team_profiles', 'game_metrics', 'games'):
            assert key in result, f"Missing key: {key}"

    def test_gci_ratings_has_teams(self):
        games, timelines = self._make_season_data()
        result = hist.compute_season_gci(games, timelines)
        assert len(result['gci_ratings']) > 0

    def test_gci_ratings_values_between_0_and_100(self):
        games, timelines = self._make_season_data()
        result = hist.compute_season_gci(games, timelines)
        for team, val in result['gci_ratings'].items():
            assert 0.0 <= val <= 100.0, f"{team} GCI={val} out of range"

    def test_game_metrics_count_matches_valid_games(self):
        games, timelines = self._make_season_data(4)
        result = hist.compute_season_gci(games, timelines)
        assert len(result['game_metrics']) == 4

    def test_games_list_contains_expected_fields(self):
        games, timelines = self._make_season_data(2)
        result = hist.compute_season_gci(games, timelines)
        for g in result['games']:
            for field in ('gamecode', 'home', 'away', 'home_score', 'away_score', 'winner'):
                assert field in g

    def test_empty_season_returns_empty_structures(self):
        result = hist.compute_season_gci({}, {})
        assert result['gci_ratings'] == {}
        assert result['game_metrics'] == {}
        assert result['games'] == []

    def test_team_profiles_include_all_teams(self):
        games, timelines = self._make_season_data(4)
        result = hist.compute_season_gci(games, timelines)
        # All teams that appear in games should have a profile
        all_teams = set()
        for g in games.values():
            all_teams.add(g['home'])
            all_teams.add(g['away'])
        for team in all_teams:
            assert team in result['team_profiles'], f"{team} missing from team_profiles"


# ---------------------------------------------------------------------------
# 5. compute_league_trends
# ---------------------------------------------------------------------------

class TestComputeLeagueTrends:
    def _make_season_result(self, season, n_games=10, avg_drama=2.5, comeback_fraction=0.1):
        """Build a mock season result dict."""
        gci_ratings = {'T1': 60.0, 'T2': 50.0, 'T3': 40.0}
        game_metrics = {
            str(i): {
                'drama': avg_drama,
                'comeback': 0.85 if i < max(1, int(n_games * comeback_fraction)) else 0.3,
                'dominance': 0.1,
            }
            for i in range(n_games)
        }
        games_list = [
            {
                'gamecode': str(i),
                'home': 'T1', 'away': 'T2',
                'home_score': 80, 'away_score': 70,
                'winner': 'T1',
            }
            for i in range(n_games)
        ]
        return {
            'season': season,
            'gci_ratings': gci_ratings,
            'components': {},
            'team_profiles': {},
            'game_metrics': game_metrics,
            'games': games_list,
        }

    def test_returns_dict_with_required_keys(self):
        sr = {2020: self._make_season_result(2020), 2021: self._make_season_result(2021)}
        result = hist.compute_league_trends(sr)
        for key in ('seasons', 'avg_drama', 'comeback_count', 'avg_gci_spread', 'game_count'):
            assert key in result, f"Missing key: {key}"

    def test_seasons_list_matches_input(self):
        sr = {2020: self._make_season_result(2020), 2022: self._make_season_result(2022)}
        result = hist.compute_league_trends(sr)
        assert set(result['seasons']) == {2020, 2022}

    def test_avg_drama_computed_per_season(self):
        sr = {
            2020: self._make_season_result(2020, n_games=4, avg_drama=2.0),
            2021: self._make_season_result(2021, n_games=4, avg_drama=4.0),
        }
        result = hist.compute_league_trends(sr)
        dramas = dict(zip(result['seasons'], result['avg_drama']))
        assert dramas[2020] == pytest.approx(2.0, abs=0.01)
        assert dramas[2021] == pytest.approx(4.0, abs=0.01)

    def test_game_count_per_season(self):
        sr = {
            2020: self._make_season_result(2020, n_games=5),
            2021: self._make_season_result(2021, n_games=8),
        }
        result = hist.compute_league_trends(sr)
        counts = dict(zip(result['seasons'], result['game_count']))
        assert counts[2020] == 5
        assert counts[2021] == 8

    def test_comeback_count_non_negative(self):
        sr = {2020: self._make_season_result(2020)}
        result = hist.compute_league_trends(sr)
        for val in result['comeback_count']:
            assert val >= 0

    def test_avg_gci_spread_non_negative(self):
        sr = {2020: self._make_season_result(2020)}
        result = hist.compute_league_trends(sr)
        for val in result['avg_gci_spread']:
            assert val >= 0

    def test_empty_input_returns_empty_lists(self):
        result = hist.compute_league_trends({})
        assert result['seasons'] == []
        assert result['avg_drama'] == []
        assert result['comeback_count'] == []
        assert result['avg_gci_spread'] == []
        assert result['game_count'] == []

    def test_seasons_list_is_sorted(self):
        sr = {
            2022: self._make_season_result(2022),
            2018: self._make_season_result(2018),
            2015: self._make_season_result(2015),
        }
        result = hist.compute_league_trends(sr)
        assert result['seasons'] == sorted(result['seasons'])


# ---------------------------------------------------------------------------
# 6. compute_team_trends
# ---------------------------------------------------------------------------

class TestComputeTeamTrends:
    def _profile_with_games(self, n_wins=5, n_losses=5, dom=0.1, drama=2.5):
        games = []
        wins = []
        losses = []
        for i in range(n_wins):
            entry = {
                'gamecode': str(i), 'opponent': 'X', 'is_home': True, 'is_win': True,
                'dominance': dom, 'control': 0.4, 'drama': drama,
                'comeback': 0.3, 'crunch': 0.05, 'killer': 0.1,
                'home_score': 80, 'away_score': 70,
            }
            games.append(entry)
            wins.append(entry)
        for i in range(n_losses):
            entry = {
                'gamecode': str(n_wins + i), 'opponent': 'Y', 'is_home': False, 'is_win': False,
                'dominance': -dom, 'control': 0.3, 'drama': drama,
                'comeback': 0.0, 'crunch': -0.05, 'killer': 0.0,
                'home_score': 70, 'away_score': 80,
            }
            games.append(entry)
            losses.append(entry)
        return {
            'games': games, 'wins': wins, 'losses': losses,
            'home_games': wins, 'away_games': losses,
        }

    def _make_season_result(self, season, teams=('OLY', 'BAR', 'MAD')):
        profiles = {t: self._profile_with_games() for t in teams}
        return {
            'season': season,
            'gci_ratings': {t: 50.0 + i * 5 for i, t in enumerate(teams)},
            'components': {t: {
                'dominance_avg': 0.05, 'control_pct': 0.35,
                'crunch_swing_avg': 0.02, 'killer_instinct': 0.05,
            } for t in teams},
            'team_profiles': profiles,
            'game_metrics': {},
            'games': [],
        }

    def test_returns_dict(self):
        sr = {2020: self._make_season_result(2020), 2021: self._make_season_result(2021)}
        result = hist.compute_team_trends(sr, min_seasons=1)
        assert isinstance(result, dict)

    def test_team_appears_if_enough_seasons(self):
        sr = {
            2020: self._make_season_result(2020, teams=('OLY',)),
            2021: self._make_season_result(2021, teams=('OLY',)),
            2022: self._make_season_result(2022, teams=('OLY',)),
        }
        result = hist.compute_team_trends(sr, min_seasons=3)
        assert 'OLY' in result

    def test_team_excluded_if_too_few_seasons(self):
        sr = {
            2020: self._make_season_result(2020, teams=('OLY',)),
            2021: self._make_season_result(2021, teams=('OLY',)),
        }
        result = hist.compute_team_trends(sr, min_seasons=3)
        assert 'OLY' not in result

    def test_trend_entry_has_seasons_and_gci_arrays(self):
        sr = {s: self._make_season_result(s, teams=('OLY',)) for s in range(2020, 2024)}
        result = hist.compute_team_trends(sr, min_seasons=1)
        entry = result['OLY']
        assert 'seasons' in entry
        assert 'gci' in entry
        assert len(entry['seasons']) == len(entry['gci'])

    def test_gci_array_length_matches_appearances(self):
        sr = {
            2020: self._make_season_result(2020, teams=('OLY', 'BAR')),
            2021: self._make_season_result(2021, teams=('OLY',)),  # BAR absent
            2022: self._make_season_result(2022, teams=('OLY', 'BAR')),
        }
        result = hist.compute_team_trends(sr, min_seasons=1)
        # OLY appears 3 seasons
        assert len(result['OLY']['seasons']) == 3
        # BAR appears 2 seasons
        assert len(result['BAR']['seasons']) == 2

    def test_seasons_are_sorted(self):
        sr = {s: self._make_season_result(s, teams=('OLY',)) for s in [2022, 2018, 2020]}
        result = hist.compute_team_trends(sr, min_seasons=1)
        assert result['OLY']['seasons'] == sorted(result['OLY']['seasons'])


# ---------------------------------------------------------------------------
# 7. find_historical_superlatives
# ---------------------------------------------------------------------------

class TestFindHistoricalSuperlatives:
    def _make_game_entry(self, gc, home, away, hs, as_, drama=2.0, dominance=0.1, comeback=0.3):
        return {
            'gamecode': gc,
            'home': home, 'away': away,
            'home_score': hs, 'away_score': as_,
            'winner': home if hs > as_ else away,
            'drama': drama,
            'dominance': dominance,
            'comeback': comeback,
        }

    def _make_season_result(self, season, games_list):
        game_metrics = {
            g['gamecode']: {
                'drama': g['drama'],
                'dominance': g['dominance'],
                'comeback': g['comeback'],
            }
            for g in games_list
        }
        return {
            'season': season,
            'gci_ratings': {},
            'components': {},
            'team_profiles': {},
            'game_metrics': game_metrics,
            'games': games_list,
        }

    def test_returns_dict_with_four_superlatives(self):
        games = [
            self._make_game_entry('1', 'OLY', 'BAR', 90, 70, drama=3.0, dominance=0.3, comeback=0.4),
            self._make_game_entry('2', 'MAD', 'CSK', 75, 74, drama=5.0, dominance=0.05, comeback=0.9),
        ]
        sr = {2020: self._make_season_result(2020, games)}
        result = hist.find_historical_superlatives(sr)
        assert isinstance(result, dict)
        assert len(result) == 4

    def test_most_dramatic_game_has_highest_drama(self):
        games = [
            self._make_game_entry('1', 'OLY', 'BAR', 90, 70, drama=3.0),
            self._make_game_entry('2', 'MAD', 'CSK', 75, 74, drama=7.5),
            self._make_game_entry('3', 'PAN', 'AXA', 80, 78, drama=5.0),
        ]
        sr = {2020: self._make_season_result(2020, games)}
        result = hist.find_historical_superlatives(sr)
        assert result['most_dramatic']['gamecode'] == '2'
        assert result['most_dramatic']['drama'] == pytest.approx(7.5, abs=0.01)

    def test_most_dominant_game_has_highest_abs_dominance(self):
        games = [
            self._make_game_entry('1', 'OLY', 'BAR', 90, 60, dominance=0.35),
            self._make_game_entry('2', 'MAD', 'CSK', 80, 70, dominance=0.2),
            self._make_game_entry('3', 'PAN', 'AXA', 70, 50, dominance=-0.4),  # Away dominated
        ]
        sr = {2020: self._make_season_result(2020, games)}
        result = hist.find_historical_superlatives(sr)
        assert result['most_dominant']['gamecode'] == '3'

    def test_biggest_comeback_exceeds_threshold(self):
        games = [
            self._make_game_entry('1', 'OLY', 'BAR', 90, 80, comeback=0.55),
            self._make_game_entry('2', 'MAD', 'CSK', 85, 75, comeback=0.92),
        ]
        sr = {2020: self._make_season_result(2020, games)}
        result = hist.find_historical_superlatives(sr)
        assert result['biggest_comeback']['gamecode'] == '2'
        assert result['biggest_comeback']['comeback'] == pytest.approx(0.92, abs=0.01)

    def test_works_across_multiple_seasons(self):
        games_2020 = [self._make_game_entry('1', 'OLY', 'BAR', 90, 70, drama=3.0)]
        games_2021 = [self._make_game_entry('2', 'MAD', 'CSK', 75, 74, drama=8.0)]
        sr = {
            2020: self._make_season_result(2020, games_2020),
            2021: self._make_season_result(2021, games_2021),
        }
        result = hist.find_historical_superlatives(sr)
        # Most dramatic should come from 2021
        assert result['most_dramatic']['gamecode'] == '2'

    def test_superlatives_include_season_field(self):
        games = [self._make_game_entry('1', 'OLY', 'BAR', 90, 70, drama=4.0, comeback=0.7)]
        sr = {2023: self._make_season_result(2023, games)}
        result = hist.find_historical_superlatives(sr)
        for key in ('most_dramatic', 'most_dominant', 'biggest_comeback'):
            if result[key] is not None:
                assert 'season' in result[key], f"{key} missing 'season' field"

    def test_empty_input_returns_none_values(self):
        result = hist.find_historical_superlatives({})
        for val in result.values():
            assert val is None

    def test_highest_gci_season_present(self):
        """The 4th superlative should identify the season/team with highest GCI."""
        sr = {
            2020: {
                'season': 2020, 'gci_ratings': {'OLY': 75.0, 'BAR': 50.0},
                'components': {}, 'team_profiles': {}, 'game_metrics': {}, 'games': [],
            },
            2021: {
                'season': 2021, 'gci_ratings': {'MAD': 90.0, 'CSK': 55.0},
                'components': {}, 'team_profiles': {}, 'game_metrics': {}, 'games': [],
            },
        }
        result = hist.find_historical_superlatives(sr)
        assert 'highest_gci' in result
        assert result['highest_gci'] is not None
        assert result['highest_gci']['gci'] == pytest.approx(90.0, abs=0.1)


# ---------------------------------------------------------------------------
# 8. Integration: real data smoke test (2024 season, fast)
# ---------------------------------------------------------------------------

class TestRealDataSmoke:
    """Light integration tests using actual 2024 season replay files."""

    SEASON_DIR = os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'data', '2024'
    )

    @pytest.fixture(scope='class')
    def season_2024(self):
        if not os.path.isdir(self.SEASON_DIR):
            pytest.skip("2024 season data not available")
        games, timelines = hist.load_season_games(self.SEASON_DIR)
        return games, timelines

    def test_loads_substantial_number_of_games(self, season_2024):
        games, timelines = season_2024
        assert len(games) >= 200, f"Expected >= 200 games, got {len(games)}"

    def test_all_games_have_valid_winner(self, season_2024):
        games, _ = season_2024
        for gc, g in games.items():
            assert g['winner'] in (g['home'], g['away']), f"{gc}: winner {g['winner']} not in teams"

    def test_compute_season_gci_runs_without_error(self, season_2024):
        games, timelines = season_2024
        result = hist.compute_season_gci(games, timelines)
        assert len(result['gci_ratings']) > 0

    def test_real_gci_ratings_in_range(self, season_2024):
        games, timelines = season_2024
        result = hist.compute_season_gci(games, timelines)
        for team, val in result['gci_ratings'].items():
            assert 0.0 <= val <= 100.0, f"{team}: GCI={val}"
