SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;


CREATE TABLE `oyids` (
  `oyid` varchar(255) NOT NULL,
  `ctime` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `playlists` (
  `id` varchar(255) NOT NULL,
  `place` enum('yotube','archive','vk') NOT NULL,
  `channel_id` varchar(255) DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `status` set('error','checked') DEFAULT NULL,
  `ctime` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `playlists_members` (
  `playlist_id` varchar(255) NOT NULL,
  `video_id` varchar(255) NOT NULL,
  `position` int(11) NOT NULL,
  `status` set('error','ok') DEFAULT NULL,
  `ctime` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `videos` (
  `id` varchar(255) NOT NULL,
  `oyid` varchar(255) NOT NULL,
  `place` enum('yotube','archive','vk') NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `video_md5` varchar(255) NOT NULL,
  `lang` varchar(255) DEFAULT NULL,
  `license` varchar(255) DEFAULT NULL,
  `subject-old` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `external-identifier-old` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `storage` varchar(255) DEFAULT NULL,
  `status` set('checked','downloaded') DEFAULT NULL,
  `ctime` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


ALTER TABLE `oyids`
  ADD PRIMARY KEY (`oyid`(20));

ALTER TABLE `playlists`
  ADD PRIMARY KEY (`id`(40),`place`) USING BTREE;

ALTER TABLE `playlists_members`
  ADD KEY `playlist_id` (`playlist_id`);

ALTER TABLE `videos`
  ADD PRIMARY KEY (`id`(16),`place`) USING BTREE,
  ADD KEY `oyid` (`oyid`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
