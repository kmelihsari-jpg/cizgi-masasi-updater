-- Ziyaret sayaci tablolari (sadece ekleme; mevcut tablolara dokunmaz).
CREATE TABLE IF NOT EXISTS visit_sessions (
  sid TEXT PRIMARY KEY,
  vid TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  active_sec INTEGER NOT NULL DEFAULT 0,
  hits INTEGER NOT NULL DEFAULT 0,
  device TEXT, os TEXT, browser TEXT, screen TEXT,
  country TEXT, city TEXT, lang TEXT,
  nick TEXT NOT NULL DEFAULT '',
  page TEXT, ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_visit_sessions_last ON visit_sessions(last_seen);
CREATE INDEX IF NOT EXISTS idx_visit_sessions_vid ON visit_sessions(vid);
CREATE TABLE IF NOT EXISTS visit_pages (
  day TEXT NOT NULL,
  page TEXT NOT NULL,
  sec INTEGER NOT NULL DEFAULT 0,
  views INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, page)
);
