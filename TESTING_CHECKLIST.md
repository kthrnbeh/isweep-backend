# ISweep Testing Checklist

## ✅ Pre-Flight Check

Before testing, verify:

- [ ] Backend running: `python -m app --port 8001 --no-reload`
- [ ] Backend healthy: http://127.0.0.1:8001/health (should return JSON)
- [ ] Extension loaded: `chrome://extensions/` shows ISweep
- [ ] DevTools open: F12 in Chrome

---

## 🧪 Test 1: HTML5 Video Filtering

### Setup (1 min)
1. Click ISweep icon → **⚙️ Preferences**
2. Find **Language** category
3. Add blocked word: `profanity`
4. Click **Save Settings**
5. Return to popup → **Enable ISweep**

### Run Test (2 min)
1. Open `file:///c:/ISweep_wireframe/isweep-backend/test.html` in Chrome
2. Play video
3. Wait 3-6 seconds for caption "profanity" to appear
4. **Expected:** Video mutes + "MUTED" text appears

### Expected Logs
```
[ISweep] Detected 1 video(s)
[ISweep] Loaded 6 caption cues
[ISweep] Video 0 started playing
[ISweep] Caption: "The next word will trigger ISweep: profanity"
[ISweep] Action: mute - Blocked word match: 'profanity'
```

### Verify Success ✓
- [ ] Green badge appears on video
- [ ] "MUTED" text shows in center when caption appears
- [ ] Video audio mutes
- [ ] Popup shows "Actions Applied: 1"
- [ ] Console shows all logs above

---

## 🎬 Test 2: YouTube Filtering

### Setup (2 min)
1. Go to https://youtube.com
2. Search for: `music video` (or `song`, `beat`, anything with repeated words)
3. Click first result to play
4. Enable captions: Click **CC** button (bottom right of video)
5. Click ISweep icon → Add blocked word: `music`
6. Click **Save Settings** → **Enable ISweep**

### Run Test (2 min)
1. Play video
2. Watch for captions with word "music"
3. **Expected:** Video mutes when "music" appears in captions

### Expected Logs
```
[ISweep-YT] Initializing YouTube handler
[ISweep-YT] Caption monitoring started
[ISweep-YT] Caption: "..."
[ISweep-YT] Action: mute - Blocked word match: 'music'
```

### Verify Success ✓
- [ ] Green badge appears on YouTube video
- [ ] Captions are visible at bottom
- [ ] When blocked word appears → "MUTED" text shows
- [ ] Video audio mutes
- [ ] Stats increment in popup
- [ ] Console shows YouTube logs

---

## 🔄 Test Different Actions

After HTML5 & YouTube work, test each action:

### Action 1: Mute (Default)
- [ ] Set Language → **Mute** for **4** seconds
- [ ] Test: Video should mute for ~4 seconds then unmute

### Action 2: Skip
- [ ] Set Sexual → **Skip** for **30** seconds
- [ ] Test: Video should jump forward 30 seconds instantly

### Action 3: Fast-Forward
- [ ] Set Violence → **Fast-forward** for **10** seconds
- [ ] Test: Video should speed up 2x for ~10 seconds

---

## 🐛 Troubleshooting Guide

### Video not detected?
```
Problem: Console shows "Detected 0 videos"
Solution: 
- Reload page
- Check file has <video> tag
- Verify <track> element exists
```

### Captions not loading?
```
Problem: No "[ISweep] Loaded X caption cues" log
Solution:
- Create captions.vtt in same folder as test.html
- Check file path: c:/ISweep_wireframe/isweep-backend/captions.vtt
- Open DevTools → Network tab → Look for captions.vtt request
```

### No filtering when captions appear?
```
Problem: Caption text shows but no muting
Solution:
- Check blocked word matches caption (case-insensitive)
- Verify ISweep is "Active" (green dot in popup)
- Check backend running: http://127.0.0.1:8001/health
- Look for API errors in Network tab
```

### YouTube not detected?
```
Problem: "[ISweep-YT]" logs don't appear
Solution:
- Reload YouTube page
- Reload extension: chrome://extensions/ → reload
- Check console for errors
- Try different YouTube video
```

### Backend connection error?
```
Problem: Network errors in DevTools
Solution:
- Start backend: python -m app --port 8001 --no-reload
- Verify URL in popup: http://127.0.0.1:8001
- Check firewall allowing localhost
- Try: http://127.0.0.1:8001/health in browser
```

---

## 📊 Quick Performance Check

### Stats Should Show:
- **Videos Detected:** Number of videos found on page
- **Actions Applied:** Number of times filter was applied

### These should increment as:
1. Load page → Videos Detected: 1
2. Blocked word appears → Actions Applied: 1
3. Again → Actions Applied: 2

---

## 🎯 Full Test Flow (5-10 min)

```
1. Start Backend (1 min)
   python -m app --port 8001 --no-reload
   
2. Setup Extension (2 min)
   - Add blocked word "profanity"
   - Enable ISweep
   
3. Test HTML5 (2 min)
   - Open test.html
   - Play video
   - Verify muting works
   
4. Test YouTube (3-5 min)
   - Go to YouTube.com
   - Find music video with captions
   - Add blocked word "music"
   - Verify muting works
   
5. Verify Stats
   - Check popup shows actions applied
```

---

## ✨ Success Criteria (All Green)

- [ ] HTML5 video filtering works
- [ ] YouTube video filtering works
- [ ] Visual feedback appears ("MUTED", "SKIPPED")
- [ ] Stats update correctly
- [ ] Console shows no errors
- [ ] Actions apply correctly (mute/skip/speed)

If all 6 are checked, **ISweep is fully functional!** 🎉

---

## 📝 Notes for Testing

- **Timing:** Captions may take 1-2 seconds to appear after video starts
- **Throttling:** ISweep waits 500ms between checks to avoid spam
- **Case-insensitive:** "Profanity", "PROFANITY", "profanity" all match
- **Multiple words:** If you add "music, song, beat" → all trigger
- **Disable/Enable:** Toggle ISweep without reloading page

---

Good luck testing! Report any issues. 🚀
