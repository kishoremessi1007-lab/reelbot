PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Genres catalog
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    typical_styles TEXT DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. Series master table
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    primary_genre TEXT NOT NULL,
    secondary_genre TEXT DEFAULT NULL,
    art_style TEXT NOT NULL,
    concept TEXT NOT NULL,
    world_setting TEXT NOT NULL,
    central_conflict TEXT NOT NULL,
    total_episodes INTEGER NOT NULL DEFAULT 6,
    current_episode INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'failed')),
    seed INTEGER NOT NULL DEFAULT 42,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_series_status ON series(status);
CREATE INDEX IF NOT EXISTS idx_series_genre ON series(primary_genre);

-- 3. Genre usage history (for rotation and avoiding repetition)
CREATE TABLE IF NOT EXISTS genre_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    primary_genre TEXT NOT NULL,
    secondary_genre TEXT DEFAULT NULL,
    art_style TEXT NOT NULL,
    selected_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_genre_history_selected ON genre_history(selected_at DESC);

-- 4. Story bibles
CREATE TABLE IF NOT EXISTS story_bibles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL UNIQUE,
    logline TEXT NOT NULL,
    beginning_arc TEXT NOT NULL,
    middle_arc TEXT NOT NULL,
    ending_arc TEXT NOT NULL,
    world_rules TEXT NOT NULL,
    themes TEXT NOT NULL,
    episode_outlines_json TEXT NOT NULL,
    unresolved_mysteries_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

-- 5. Characters
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_uid TEXT NOT NULL UNIQUE,
    series_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'supporting' CHECK (role IN ('protagonist', 'antagonist', 'supporting')),
    age TEXT NOT NULL,
    gender TEXT NOT NULL,
    personality TEXT NOT NULL,
    physical_appearance TEXT NOT NULL,
    hairstyle TEXT NOT NULL,
    hair_color TEXT NOT NULL,
    eye_color TEXT NOT NULL,
    clothing TEXT NOT NULL,
    accessories TEXT NOT NULL,
    height_proportions TEXT NOT NULL,
    background TEXT NOT NULL,
    goals TEXT NOT NULL,
    weaknesses TEXT NOT NULL,
    abilities TEXT NOT NULL,
    relationships_json TEXT NOT NULL DEFAULT '{}',
    character_development TEXT NOT NULL,
    visual_prompt_token TEXT NOT NULL,
    seed INTEGER NOT NULL DEFAULT 1001,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_characters_series ON characters(series_id);

-- 6. Character reference sheets
CREATE TABLE IF NOT EXISTS character_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    series_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    public_url TEXT DEFAULT NULL,
    prompt_used TEXT NOT NULL,
    negative_prompt TEXT NOT NULL DEFAULT '',
    seed INTEGER NOT NULL,
    width INTEGER NOT NULL DEFAULT 1080,
    height INTEGER NOT NULL DEFAULT 1350,
    generator_backend TEXT NOT NULL DEFAULT 'comfyui',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_char_refs_char ON character_references(character_id);

-- 7. Episodes
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    previous_summary TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    emotional_beats_json TEXT NOT NULL DEFAULT '[]',
    ending_cliffhanger TEXT NOT NULL DEFAULT '',
    script_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scripted' CHECK (status IN ('scripted', 'art_generated', 'composed', 'qc_passed', 'qc_failed', 'published', 'failed')),
    qc_report_json TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(series_id, episode_number),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_id, episode_number);

-- 8. Scenes within episodes
CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    scene_number INTEGER NOT NULL,
    location TEXT NOT NULL,
    time_of_day TEXT NOT NULL DEFAULT 'day',
    mood TEXT NOT NULL DEFAULT 'dramatic',
    description TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scenes_episode ON scenes(episode_id);

-- 9. Comic panels / slides
CREATE TABLE IF NOT EXISTS comic_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    scene_id INTEGER DEFAULT NULL,
    panel_order INTEGER NOT NULL,
    format_type TEXT NOT NULL DEFAULT 'carousel' CHECK (format_type IN ('carousel', 'individual')),
    panel_description TEXT NOT NULL,
    character_positions TEXT NOT NULL DEFAULT '',
    character_expressions TEXT NOT NULL DEFAULT '',
    camera_angle TEXT NOT NULL DEFAULT 'medium shot',
    background_description TEXT NOT NULL DEFAULT '',
    dialogue_json TEXT NOT NULL DEFAULT '[]',
    narration TEXT NOT NULL DEFAULT '',
    sound_effects_json TEXT NOT NULL DEFAULT '[]',
    characters_present_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_panels_episode ON comic_panels(episode_id, format_type, panel_order);

-- 10. Generated images (raw artwork and final composed slides/pages)
CREATE TABLE IF NOT EXISTS generated_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    episode_id INTEGER DEFAULT NULL,
    panel_id INTEGER DEFAULT NULL,
    image_role TEXT NOT NULL CHECK (image_role IN ('character_ref', 'raw_panel', 'carousel_slide', 'individual_page')),
    slide_number INTEGER DEFAULT NULL,
    file_path TEXT NOT NULL,
    public_url TEXT DEFAULT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    checksum_sha256 TEXT NOT NULL DEFAULT '',
    prompt_used TEXT DEFAULT '',
    seed INTEGER DEFAULT NULL,
    generator_backend TEXT NOT NULL DEFAULT 'comfyui',
    qc_passed INTEGER NOT NULL DEFAULT 0,
    qc_notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id) REFERENCES comic_panels(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_gen_images_episode ON generated_images(episode_id, image_role);

-- 11. Carousel posts
CREATE TABLE IF NOT EXISTS carousel_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL UNIQUE,
    caption TEXT NOT NULL,
    hashtags TEXT NOT NULL,
    slide_image_ids_json TEXT NOT NULL,
    slide_urls_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'scheduled', 'publishing', 'published', 'failed')),
    instagram_media_id TEXT DEFAULT NULL,
    published_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

-- 12. Individual comic-page posts
CREATE TABLE IF NOT EXISTS individual_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL UNIQUE,
    caption TEXT NOT NULL,
    hashtags TEXT NOT NULL,
    image_id INTEGER NOT NULL,
    public_url TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'scheduled', 'publishing', 'published', 'failed')),
    instagram_media_id TEXT DEFAULT NULL,
    published_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES generated_images(id) ON DELETE CASCADE
);

-- 13. Publishing queue (with idempotency_key to prevent duplicate publishing)
CREATE TABLE IF NOT EXISTS publishing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    series_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL,
    post_format TEXT NOT NULL CHECK (post_format IN ('carousel', 'individual')),
    post_ref_id INTEGER NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'published', 'failed', 'cancelled')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    last_error TEXT DEFAULT NULL,
    instagram_media_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pub_queue_status_time ON publishing_queue(status, scheduled_for);

-- 14. Instagram accounts
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ig_user_id TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL DEFAULT '',
    account_type TEXT NOT NULL DEFAULT 'BUSINESS',
    token_expires_at TEXT DEFAULT NULL,
    last_token_check_at TEXT DEFAULT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 15. Publishing logs
CREATE TABLE IF NOT EXISTS publishing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id INTEGER DEFAULT NULL,
    series_id INTEGER DEFAULT NULL,
    episode_id INTEGER DEFAULT NULL,
    post_format TEXT DEFAULT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    http_status INTEGER DEFAULT NULL,
    response_payload TEXT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (queue_id) REFERENCES publishing_queue(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pub_logs_created ON publishing_logs(created_at DESC);

-- 16. Automation runs
CREATE TABLE IF NOT EXISTS automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL,
    trigger_source TEXT NOT NULL DEFAULT 'scheduler',
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    series_id INTEGER DEFAULT NULL,
    episode_id INTEGER DEFAULT NULL,
    details_json TEXT DEFAULT '{}',
    error_message TEXT DEFAULT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_auto_runs_started ON automation_runs(started_at DESC);

-- 17. Story continuity memory
CREATE TABLE IF NOT EXISTS story_continuity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL UNIQUE,
    current_episode_number INTEGER NOT NULL DEFAULT 0,
    last_episode_summary TEXT NOT NULL DEFAULT '',
    last_cliffhanger TEXT NOT NULL DEFAULT '',
    unresolved_mysteries_json TEXT NOT NULL DEFAULT '[]',
    character_states_json TEXT NOT NULL DEFAULT '{}',
    future_plot_hooks_json TEXT NOT NULL DEFAULT '[]',
    published_post_ids_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

-- App settings key-value store (configurable via dashboard)
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
