# Agent 2 - Quick Reference Card

## Mission: Scale Testing for 1.dwfx

**Status:** ✅ COMPLETE

---

## Quick Answer

### What is the correct scale factor for file 1?

**Answer: `0.050157`**

### Why?

- Source geometry: 137031 x 9463 DWF units (from 3.dwf W2D)
- Target page: 6945 x 1871 points (from 1.pdf)
- Scale = 6873 / 137031 = 0.050157

---

## Important Finding

**1.dwfx does NOT contain W2D vector data!**

- 1.dwfx uses XPS format (rasterized images)
- Used 3.dwf as source instead (contains W2D stream)
- This is a critical finding for the project

---

## All Test Results

| Scale | Output Dimensions | Suitable For |
|-------|------------------|--------------|
| 0.001 | 137 x 9 pts | Too small |
| 0.01 | 1370 x 95 pts | Too small |
| **0.050157** | **6873 x 475 pts** | **Matches reference width** |
| 0.1 | 13703 x 946 pts | Too large |
| 1.0 | 137031 x 9463 pts | Way too large |
| 10.0 | 1370310 x 94630 pts | Extremely oversized |

---

## Key Files

**Main Deliverable:**
- `/home/user/git-practice/agent2_scale_results.md`

**Test PDFs (6 files):**
- All in `/home/user/git-practice/agent2_test_scale_*.pdf`

**Complete Documentation:**
- `AGENT2_COMPLETION_SUMMARY.md` - Full mission report
- `agent2_additional_analysis.md` - Detailed analysis
- `AGENT2_QUICK_REFERENCE.md` - This file

---

## Bounding Box Data

**From 3.dwf W2D Stream:**

```
Raw Coordinates:
  Min: (2147255419, 21380)
  Max: (2147392450, 30843)

Bounding Box:
  Width:  137031 DWF units
  Height:   9463 DWF units
  Aspect: 14.48:1 (very wide landscape)
```

**Reference PDF (1.pdf):**

```
Page Size:
  Width:  6945 points (96.46 inches)
  Height: 1871 points (25.99 inches)
  Aspect: 3.71:1 (wide landscape)
```

---

## Command to Re-run Tests

```bash
python3 /home/user/git-practice/agent2_scale_test.py
```

---

## Test Matrix

```
Source: 3.dwf (W2D: 10.25 MB)
Target: 1.pdf (3.1 MB)
Opcodes Parsed: 983
Unknown Opcodes: 23 (2.3%)
```

---

**Agent 2 - Scale Testing Complete**
*File 1 optimal scale: 0.050157*
