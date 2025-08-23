# SERP Radio Real-Data Demo Guide

## Purpose
Create a compelling demo using actual GSC data to show stakeholders the real-world application.

## Step-by-Step Process

### 1. Export GSC Data
1. **Login** to Google Search Console
2. **Navigate** to Performance → Search Results
3. **Set Date Range** to last 90 days
4. **Add Filters**:
   - Query (to get keyword data)
   - Page (optional, for specific landing pages)
5. **Export** → "Export as CSV"
6. **Expected columns**: Date, Query, Clicks, Impressions, Position

### 2. Prepare Demo CSV
```bash
# Typical GSC export will have these columns:
# Date,Query,Clicks,Impressions,Position

# Example content:
2024-10-01,ai tools,45,2500,2.1
2024-10-01,machine learning,23,1200,3.8
2024-10-01,data science,67,3200,1.5
2024-10-01,python programming,34,1800,4.1
```

### 3. Upload and Listen
1. **Navigate** to `https://api.serpradio.com/widget/`
2. **Select** "Upload CSV" tab
3. **Choose** "GSC (Google Search Console)" radio button
4. **Upload** your GSC export
5. **Listen** to the sonification once
6. **Note** patterns in:
   - High-performing keywords (brighter, higher notes)
   - Click volume (louder notes)
   - Impression volume (longer note durations)

### 4. Generate Shareable MIDI
1. **After playback** completes, click "Download MIDI 🎹"
2. **Import** MIDI into GarageBand, Logic, or any DAW
3. **Add** basic drums, bass, or effects if desired
4. **Bounce** to MP3 (20-30 seconds is sufficient)
5. **Trim** to highlight the most interesting melodic sections

### 5. Create Marketing Asset
```html
<!-- Example for Lovable hero section -->
<div class="serp-radio-demo">
    <h2>🎵 Hear Your SEO Data</h2>
    <p>This 20-second audio was generated from real GSC data:</p>
    
    <audio controls preload="metadata">
        <source src="serp-radio-demo.mp3" type="audio/mpeg">
        Your browser doesn't support audio playback.
    </audio>
    
    <small>Generated from 90 days of search performance data</small>
</div>
```

## Demo Script for Stakeholders

### Opening (30 seconds)
*"What you're about to hear is 90 days of actual search performance data from [client name]. Each note represents a keyword ranking, with pitch indicating position and volume representing click-through performance."*

### During Playback (20 seconds)
*"The higher, brighter notes are top-performing keywords. The volume tells us click velocity. You can actually hear the difference between branded terms and competitive keywords."*

### Closing (10 seconds)
*"This is live CSV upload - any GSC export or rank tracker file becomes instant audio feedback. Perfect for client presentations or internal performance reviews."*

## Expected Impact

### For Investors:
- ✅ **Immediate comprehension** of complex data relationships
- ✅ **Unique positioning** vs traditional dashboards
- ✅ **"Wow factor"** demonstrates innovation
- ✅ **Practical application** shows B2B revenue potential

### For Beta Users:
- ✅ **Quick performance assessment** without reading numbers
- ✅ **Pattern recognition** across large datasets
- ✅ **Client presentation tool** for agencies
- ✅ **Memorable deliverable** (shareable MIDI files)

## Production Tips

### Best GSC Exports for Demo:
- **Time Range**: 90 days (good balance of data volume/relevance)
- **Include**: High-traffic branded terms + competitive keywords
- **Avoid**: Super long-tail (creates noise in sonification)
- **Size**: 1,000-5,000 rows ideal for 30-60 second audio

### Audio Post-Production:
- **Length**: Keep under 30 seconds for attention span
- **Volume**: Normalize to -14 LUFS for consistent playback
- **Format**: MP3 320kbps for web, WAV for presentations
- **Fade**: Add 1-second fade in/out for smooth looping

### Presentation Context:
- **Lead with problem**: "SEO reporting is overwhelming"
- **Demo the solution**: Play the audio
- **Show the process**: Upload → Listen → Download
- **Close with vision**: "Imagine every client call starting with this"

## Sample Demo Files

Place these in `/demo/samples/`:
- `sample-gsc-export.csv` (sanitized real data)
- `demo-audio-output.mp3` (rendered result)
- `demo-midi-file.mid` (downloadable version)

This creates a complete "input → process → output" demo package that stakeholders can experience end-to-end. 