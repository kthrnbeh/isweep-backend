# Database Migration Fix - January 28, 2026

## Problem Diagnosed

Your backend was crashing with:
```
sqlite3.OperationalError: no such column: caption_offset_ms
```

This happened because we added the `caption_offset_ms` column to the code, but your existing `isweep.db` database didn't have that column yet.

## Solution Implemented

### 1. Database Auto-Migration
Added automatic migration logic to `app/database.py`:

```python
def migrate_db():
    """Add missing columns to existing database tables."""
    inspector = inspect(engine)
    
    # Check if preferences table exists
    if 'preferences' not in inspector.get_table_names():
        return
    
    # Get existing columns
    existing_columns = {col['name'] for col in inspector.get_columns('preferences')}
    
    # Add caption_offset_ms column if missing
    if 'caption_offset_ms' not in existing_columns:
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE preferences ADD COLUMN caption_offset_ms INTEGER DEFAULT 300'))
            conn.commit()
        logger.info("✅ Added caption_offset_ms column")
```

This code:
- Checks if the `preferences` table exists
- Inspects existing columns
- Adds `caption_offset_ms` column if it's missing (with default value 300)
- Only runs once (won't duplicate the column)

### 2. Backend Status
✅ **Backend is now running successfully on http://127.0.0.1:8001**

The database has been migrated and the column now exists.

## Matching Behavior

### Case-Insensitivity ✅
The matching is **already case-insensitive**. The code uses `.lower()` on both the caption text and blocked words:

```python
text_lower = text.lower()
w_clean = blocked_word.strip().lower()
```

So these will ALL match if you block "god":
- "God" → matches
- "GOD" → matches  
- "god" → matches
- "Rap God" → matches the word "God" (case-insensitive)

### Word Boundary Matching ✅
The regex uses word boundaries (`\b`) to prevent partial matches:

```python
pattern = r'\b' + pattern + r'\b'
```

Examples:
- If you block **"god"** (single word):
  - ✅ Matches: "oh my God", "Rap God Rap God"
  - ❌ Does NOT match: "godlike", "demigod", "good" 

- If you block **"god damn"** (phrase):
  - ✅ Matches: "God damn it", "GOD DAMN"
  - ❌ Does NOT match: "god" alone, "damn" alone

## What You Need To Do Now

### Step 1: Reload Chrome Extension
1. Go to `chrome://extensions`
2. Find **ISweep**
3. Click the **Reload** button (circular arrow icon)

### Step 2: Add "God" to Blocked Words
1. Click the ISweep extension icon
2. Go to **Options**
3. Under **Language** section → **Custom Words**
4. Add: `god`
5. Click **Save**

### Step 3: Test on YouTube
1. Play the "Rap God" video
2. Watch the console (F12 → Console tab)
3. You should see logs like:
   ```
   [ISweep] Backend response: {action: "mute", reason: "Blocked word match: 'god' (regex: \bgod\b)"}
   [ISweep] Using caption_offset_ms: 300ms for category "language"
   ```

### Step 4: Adjust Caption Offset (if needed)
If the mute fires too early or too late:
1. Open **Options**
2. Find **Caption Offset (ms)** under Language section
3. Try different values:
   - **100ms** = mute fires earlier (if captions appear before audio)
   - **500ms** = mute fires later (if captions appear after audio)
   - Default is **300ms**

## Known Behavior

### Why "God" in "Rap God" gets caught
This is **correct behavior** based on word boundaries:
- "Rap God" contains the standalone word "God"
- The word boundary regex `\bgod\b` correctly matches it
- This is case-insensitive, so "god", "God", "GOD" all match

### If You Don't Want to Block "God" in Music Lyrics
You have a few options:

**Option A:** Use phrase matching instead
- Instead of blocking "god" alone
- Block specific phrases like:
  - "oh my god"
  - "god damn"
  - "for god's sake"
  - "god help"

**Option B:** Add context-aware rules (future feature)
- This would require adding more sophisticated NLP
- Could detect blasphemous vs. non-blasphemous usage
- Not currently implemented

**Option C:** Disable Language filtering during music
- Turn off the extension when watching music videos
- Or disable only the Language category temporarily

## Logs to Watch

When testing, watch for these console logs:

```javascript
[ISweep] Processing caption: {original: "I'm beginnin' to feel like a Rap God Rap God", normalized: "i'm beginnin' to feel like a rap god rap god"}
[ISweep] Backend response: {action: "mute", reason: "Blocked word match: 'god' (regex: \bgod\b)", matched_term: "god"}
[ISweep] Using caption_offset_ms: 300ms for category "language"
[ISweep] Mute scheduled: start in 300ms, duration 450ms (0.45s * 2 words)
```

These logs confirm:
1. ✅ Caption was captured
2. ✅ Backend matched "god" using word boundary regex
3. ✅ Caption offset is being used
4. ✅ Mute is scheduled with correct timing

## Backend is Ready

The backend is now running and fully functional:
- ✅ Database migrated with `caption_offset_ms` column
- ✅ Case-insensitive matching active
- ✅ Word boundary regex working
- ✅ No more 500 errors

**Ready for testing!**
