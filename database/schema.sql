SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;


CREATE TABLE `future_matches` (
  `match_id` int(11) NOT NULL,
  `league_id` int(11) NOT NULL,
  `home_team_id` int(11) NOT NULL,
  `away_team_id` int(11) NOT NULL,
  `match_date` datetime NOT NULL,
  `stadium` varchar(100) DEFAULT NULL,
  `referee` varchar(50) DEFAULT NULL,
  `weather_conditions` varchar(255) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `h2h_matches` (
  `id` int(11) NOT NULL,
  `fixture_id` int(11) NOT NULL,
  `league_id` int(11) NOT NULL,
  `home_team_id` int(11) NOT NULL,
  `away_team_id` int(11) NOT NULL,
  `home_goals` int(11) DEFAULT NULL,
  `away_goals` int(11) DEFAULT NULL,
  `halftime_home_goals` int(11) DEFAULT NULL,
  `halftime_away_goals` int(11) DEFAULT NULL,
  `fulltime_home_goals` int(11) DEFAULT NULL,
  `fulltime_away_goals` int(11) DEFAULT NULL,
  `extratime_home_goals` int(11) DEFAULT NULL,
  `extratime_away_goals` int(11) DEFAULT NULL,
  `penalty_home_goals` int(11) DEFAULT NULL,
  `penalty_away_goals` int(11) DEFAULT NULL,
  `match_date` datetime DEFAULT NULL,
  `season` year(4) DEFAULT NULL,
  `round` varchar(50) DEFAULT NULL,
  `venue` varchar(100) DEFAULT NULL,
  `referee` varchar(100) DEFAULT NULL,
  `yellow_cards_home` int(11) DEFAULT 0,
  `yellow_cards_away` int(11) DEFAULT 0,
  `red_cards_home` int(11) DEFAULT 0,
  `red_cards_away` int(11) DEFAULT 0,
  `fouls_home` int(11) DEFAULT 0,
  `fouls_away` int(11) DEFAULT 0,
  `winner_team_id` int(11) DEFAULT NULL,
  `last_data_insert` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `leagues` (
  `league_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `country` varchar(255) DEFAULT NULL,
  `country_code` varchar(10) DEFAULT NULL,
  `flag_url` varchar(500) DEFAULT NULL,
  `logo_url` varchar(500) DEFAULT NULL,
  `type` varchar(50) DEFAULT NULL,
  `current_season` int(11) NOT NULL DEFAULT 2024,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `matches` (
  `match_id` int(11) NOT NULL,
  `league_id` int(11) DEFAULT NULL,
  `home_team_id` int(11) DEFAULT NULL,
  `away_team_id` int(11) DEFAULT NULL,
  `date` datetime DEFAULT NULL,
  `result` enum('win','draw','loss','unknown') DEFAULT NULL,
  `score_home` int(11) DEFAULT NULL,
  `score_away` int(11) DEFAULT NULL,
  `referee_name` varchar(255) DEFAULT NULL,
  `stadium_name` varchar(255) DEFAULT NULL,
  `match_duration` int(11) DEFAULT NULL,
  `match_type` varchar(64) DEFAULT NULL,
  `penalties_awarded` int(11) DEFAULT NULL,
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `match_events` (
  `id` int(10) UNSIGNED NOT NULL,
  `match_id` int(11) NOT NULL,
  `event_time` smallint(5) UNSIGNED NOT NULL,
  `extra_time` smallint(5) UNSIGNED DEFAULT NULL,
  `event_type` enum('goal','yellow_card','red_card','second_yellow_card','penalty_goal') NOT NULL,
  `event_detail` varchar(64) NOT NULL,
  `is_penalty` tinyint(1) NOT NULL DEFAULT 0,
  `player_id` int(11) DEFAULT NULL,
  `team_id` int(11) NOT NULL,
  `assist_player_id` int(11) DEFAULT NULL,
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ;

CREATE TABLE `match_statistics` (
  `id` int(11) NOT NULL,
  `match_id` int(11) NOT NULL,
  `team_id` int(11) NOT NULL,
  `shots_on_goal` int(11) DEFAULT NULL,
  `shots_off_goal` int(11) DEFAULT NULL,
  `total_shots` int(11) DEFAULT NULL,
  `blocked_shots` int(11) DEFAULT NULL,
  `shots_inside_box` int(11) DEFAULT NULL,
  `shots_outside_box` int(11) DEFAULT NULL,
  `fouls` int(11) DEFAULT NULL,
  `corner_kicks` int(11) DEFAULT NULL,
  `offsides` int(11) DEFAULT NULL,
  `ball_possession` decimal(5,2) DEFAULT NULL,
  `yellow_cards` int(11) DEFAULT NULL,
  `red_cards` int(11) DEFAULT NULL,
  `goalkeeper_saves` int(11) DEFAULT NULL,
  `total_passes` int(11) DEFAULT NULL,
  `passes_accurate` int(11) DEFAULT NULL,
  `passes_percentage` varchar(10) DEFAULT NULL,
  `expected_goals` decimal(5,2) DEFAULT NULL,
  `goals_prevented` decimal(5,2) DEFAULT NULL,
  `last_data_insert` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `players` (
  `player_id` int(11) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `firstname` varchar(100) DEFAULT NULL,
  `lastname` varchar(100) DEFAULT NULL,
  `age` int(11) DEFAULT NULL,
  `birth_date` date DEFAULT NULL,
  `birth_place` varchar(100) DEFAULT NULL,
  `birth_country` varchar(100) DEFAULT NULL,
  `nationality` varchar(100) DEFAULT NULL,
  `height` varchar(10) DEFAULT NULL,
  `weight` varchar(10) DEFAULT NULL,
  `injured` tinyint(1) DEFAULT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `last_data_insert` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `player_statistics` (
  `id` int(11) NOT NULL,
  `player_id` int(11) NOT NULL,
  `team_id` int(11) NOT NULL,
  `league_id` int(11) NOT NULL,
  `season` int(11) NOT NULL,
  `appearances` int(11) DEFAULT NULL,
  `lineups` int(11) DEFAULT NULL,
  `minutes_played` int(11) DEFAULT NULL,
  `position` varchar(50) DEFAULT NULL,
  `rating` decimal(5,2) DEFAULT NULL,
  `goals_total` int(11) DEFAULT NULL,
  `goals_assists` int(11) DEFAULT NULL,
  `shots_total` int(11) DEFAULT NULL,
  `shots_on_target` int(11) DEFAULT NULL,
  `passes_total` int(11) DEFAULT NULL,
  `passes_key` int(11) DEFAULT NULL,
  `passes_accuracy` decimal(5,2) DEFAULT NULL,
  `tackles_total` int(11) DEFAULT NULL,
  `tackles_blocks` int(11) DEFAULT NULL,
  `tackles_interceptions` int(11) DEFAULT NULL,
  `duels_total` int(11) DEFAULT NULL,
  `duels_won` int(11) DEFAULT NULL,
  `dribbles_attempts` int(11) DEFAULT NULL,
  `dribbles_success` int(11) DEFAULT NULL,
  `fouls_committed` int(11) DEFAULT NULL,
  `fouls_drawn` int(11) DEFAULT NULL,
  `yellow_cards` int(11) DEFAULT NULL,
  `red_cards` int(11) DEFAULT NULL,
  `penalties_scored` int(11) DEFAULT NULL,
  `penalties_missed` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `predictions` (
  `id` int(11) NOT NULL,
  `fixture_id` int(11) NOT NULL,
  `winner_team_id` int(11) DEFAULT NULL,
  `winner_name` varchar(100) DEFAULT NULL,
  `advice` text DEFAULT NULL,
  `home_win_percent` decimal(5,2) DEFAULT NULL,
  `draw_percent` decimal(5,2) DEFAULT NULL,
  `away_win_percent` decimal(5,2) DEFAULT NULL,
  `goals_home` decimal(4,1) NOT NULL DEFAULT 0.0,
  `goals_away` decimal(4,1) NOT NULL DEFAULT 0.0,
  `last_data_insert` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `teams` (
  `team_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `country` varchar(100) DEFAULT NULL,
  `founded` int(11) DEFAULT NULL,
  `logo_url` varchar(255) DEFAULT NULL,
  `coach_name` varchar(255) DEFAULT NULL,
  `home_stadium` varchar(255) DEFAULT NULL,
  `stadium_capacity` int(11) DEFAULT NULL,
  `stadium_address` varchar(255) DEFAULT NULL,
  `stadium_city` varchar(100) DEFAULT NULL,
  `stadium_surface` varchar(50) DEFAULT NULL,
  `stadium_image` varchar(255) DEFAULT NULL,
  `current_form` varchar(50) DEFAULT NULL,
  `form_percentage` int(11) DEFAULT NULL,
  `play_style` enum('defensive','offensive','balanced') DEFAULT 'balanced',
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `teams_standing` (
  `id` int(11) NOT NULL,
  `league_id` int(10) UNSIGNED NOT NULL,
  `season` int(4) NOT NULL,
  `team_id` int(11) NOT NULL,
  `rank` int(3) DEFAULT 0,
  `points` int(3) DEFAULT 0,
  `form` varchar(10) DEFAULT NULL,
  `goals_for` int(3) DEFAULT 0,
  `goals_against` int(3) DEFAULT 0,
  `goals_difference` int(3) DEFAULT 0,
  `home_played` int(3) DEFAULT 0,
  `home_wins` int(3) DEFAULT 0,
  `home_draws` int(3) DEFAULT 0,
  `home_losses` int(3) DEFAULT 0,
  `home_goals_for` int(3) DEFAULT 0,
  `home_goals_against` int(3) DEFAULT 0,
  `away_played` int(3) DEFAULT 0,
  `away_wins` int(3) DEFAULT 0,
  `away_draws` int(3) DEFAULT 0,
  `away_losses` int(3) DEFAULT 0,
  `away_goals_for` int(3) DEFAULT 0,
  `away_goals_against` int(3) DEFAULT 0,
  `status` enum('up','down','same') DEFAULT 'same',
  `description` varchar(255) DEFAULT NULL,
  `last_data_insert` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;


ALTER TABLE `future_matches`
  ADD PRIMARY KEY (`match_id`),
  ADD KEY `idx_league_id` (`league_id`),
  ADD KEY `idx_match_date` (`match_date`);

ALTER TABLE `h2h_matches`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_fixture_opponent` (`fixture_id`,`home_team_id`,`away_team_id`);

ALTER TABLE `leagues`
  ADD PRIMARY KEY (`league_id`);

ALTER TABLE `matches`
  ADD PRIMARY KEY (`match_id`),
  ADD KEY `home_team_id` (`home_team_id`),
  ADD KEY `away_team_id` (`away_team_id`),
  ADD KEY `idx_matches_league_team` (`league_id`,`home_team_id`,`away_team_id`),
  ADD KEY `idx_matches_date` (`date`);

ALTER TABLE `match_events`
  ADD PRIMARY KEY (`id`),
  ADD KEY `player_id` (`player_id`),
  ADD KEY `idx_match_team` (`match_id`,`team_id`);

ALTER TABLE `match_statistics`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_match_team` (`match_id`,`team_id`),
  ADD KEY `match_id` (`match_id`),
  ADD KEY `team_id` (`team_id`);

ALTER TABLE `players`
  ADD PRIMARY KEY (`player_id`),
  ADD UNIQUE KEY `unique_player` (`firstname`,`lastname`,`birth_date`,`nationality`);

ALTER TABLE `player_statistics`
  ADD PRIMARY KEY (`id`),
  ADD KEY `player_statistics_ibfk_1` (`player_id`),
  ADD KEY `player_statistics_ibfk_2` (`team_id`),
  ADD KEY `player_statistics_ibfk_3` (`league_id`);

ALTER TABLE `predictions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `fixture_id` (`fixture_id`);

ALTER TABLE `teams`
  ADD PRIMARY KEY (`team_id`),
  ADD KEY `idx_teams_name_country` (`name`,`country`),
  ADD KEY `idx_teams_name` (`name`);

ALTER TABLE `teams_standing`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_team_season` (`team_id`,`season`,`league_id`),
  ADD KEY `idx_league_season` (`league_id`,`season`);


ALTER TABLE `h2h_matches`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `match_events`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE `match_statistics`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `player_statistics`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `predictions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `teams_standing`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;


ALTER TABLE `matches`
  ADD CONSTRAINT `matches_ibfk_1` FOREIGN KEY (`home_team_id`) REFERENCES `teams` (`team_id`),
  ADD CONSTRAINT `matches_ibfk_2` FOREIGN KEY (`away_team_id`) REFERENCES `teams` (`team_id`),
  ADD CONSTRAINT `matches_ibfk_4` FOREIGN KEY (`league_id`) REFERENCES `leagues` (`league_id`) ON DELETE CASCADE;

ALTER TABLE `match_events`
  ADD CONSTRAINT `match_events_ibfk_1` FOREIGN KEY (`match_id`) REFERENCES `matches` (`match_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `match_events_ibfk_2` FOREIGN KEY (`player_id`) REFERENCES `players` (`player_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `match_events_ibfk_3` FOREIGN KEY (`team_id`) REFERENCES `teams` (`team_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `match_events_ibfk_4` FOREIGN KEY (`assist_player_id`) REFERENCES `players` (`player_id`) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE `match_statistics`
  ADD CONSTRAINT `match_statistics_ibfk_1` FOREIGN KEY (`match_id`) REFERENCES `matches` (`match_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `match_statistics_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `teams` (`team_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `player_statistics`
  ADD CONSTRAINT `player_statistics_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `players` (`player_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `player_statistics_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `teams` (`team_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `player_statistics_ibfk_3` FOREIGN KEY (`league_id`) REFERENCES `leagues` (`league_id`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `teams_standing`
  ADD CONSTRAINT `teams_standing_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `teams` (`team_id`) ON DELETE CASCADE;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
