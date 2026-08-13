# SMDR Parsing Fix - Records Without ==SMDX Prefix

## Problem

SMDR records from Phonik PBX in the following format were not being captured:

```
10/08/26 14:54 401 e.400 EC 0:00'05 0 #1
10/08/26 17:21 401 e.400 EC 0:00'10 0 #1
10/08/26 21:04 401 e.400 EC 0:00'08 0 #1
10/08/26 22:15 401 e.400 EC 0:00'04 0 #1
```

These records **lack the `==SMDX` or `--SMDX` prefix** that the original regex expected.

## Root Cause

The original regex pattern required a prefix:

```python
SMDR_PATTERN = re.compile(
    r"[=\\-]{2}SMDX\s*\d*\s*=?\s*\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s+(\d+)\s+(\S+)"
)
```

This pattern matches:
- ✅ `==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1`
- ❌ `10/08/26 14:54 401 e.400 EC 0:00'05 0 #1` (no prefix)

While there was fallback logic to catch lines with `"e."`, it wasn't logging properly and might have had edge cases.

## Solution

### 1. Updated Regex Pattern (Make Prefix Optional)

```python
SMDR_PATTERN = re.compile(
    r"(?:[=\\-]{2}SMDX\s*\d*\s*=?\s*)?\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s+(\d+)\s+(\S+)"
)
```

The `(?:...)?` makes the entire prefix group optional, so both formats are now supported:
- ✅ `==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1`
- ✅ `10/08/26 14:54 401 e.400 EC 0:00'05 0 #1`

### 2. Enhanced Logging

Added comprehensive logging to track:
- When fallback parsing is used
- Which lines are ignored and why
- All incoming lines at debug level
- Warnings when lines contain "e." but fail to parse

```python
if not match:
    if "e." in line:
        logging.debug(f"SMDR regex failed but 'e.' found, using fallback: {line[:100]}")
        room_match = re.search(r"e\.(\d+)", line)
        if room_match:
            room_id = room_match.group(1)
            logging.info(f"Fallback parsing successful: Room {room_id} from line: {line[:80]}")
            return self._create_event_payload(room_id, "CALL_BEDSIDE", line)
    else:
        logging.debug(f"SMDR line ignored (no match): {line[:100]}")
    return None
```

### 3. Debug Logging in _process_line

```python
async def _process_line(self, raw_line: str):
    # Log all incoming lines for debugging
    logging.debug(f"Processing line: {raw_line[:150]}")
    
    event_data = self.parse_smdr_line(raw_line)
    if event_data:
        logging.info(f"SNC Event Detected: Room {event_data['extension']['roomId']} -> ...")
        await self.send_event_to_backend(event_data)
    else:
        if "e." in raw_line and not PhonikTelnetSession.is_banner_line(raw_line):
            logging.warning(f"Line contains 'e.' but failed to parse: {raw_line[:150]}")
```

## Testing

Run the updated test suite:

```bash
cd snc-poc/pbx-connector
python -m pytest test_smdr_parser.py -v
```

Or run the debug script:

```bash
python debug_smdr_records.py
```

Expected output:
```
Test 1: 10/08/26 14:54 401 e.400 EC 0:00'05 0 #1
  ✅ PARSED SUCCESSFULLY
     Room ID: 0400
     Event Type: CALL_BEDSIDE
     Status: active
```

## Deployment

After making these changes:

1. **Stop current listener**:
   ```bash
   pkill -f snc_pbx_listener
   ```

2. **Copy updated file to Pi**:
   ```bash
   scp snc_pbx_listener.py pi@192.168.1.94:/home/pi/Hotel-ECS/snc-poc/pbx-connector/
   ```

3. **Restart listener**:
   ```bash
   ./start-snc-system.sh
   ```

4. **Monitor logs**:
   ```bash
   tail -f /home/pi/Hotel-ECS/logs/pbx_listener.log | grep -E "(SMDR|Event Detected|Fallback)"
   ```

5. **Verify events appear**:
   - Check dashboard for new events
   - Or query API: `curl http://localhost:8000/api/events | python3 -m json.tool`

## Verification Checklist

- [ ] Updated regex pattern supports both formats
- [ ] Enhanced logging added to parse_smdr_line
- [ ] Debug logging added to _process_line
- [ ] Test cases added for no-prefix format
- [ ] File deployed to Raspberry Pi
- [ ] Listener restarted successfully
- [ ] Events appearing in logs
- [ ] Events visible on dashboard
- [ ] No errors in backend logs

## Files Modified

1. `snc-poc/pbx-connector/snc_pbx_listener.py`
   - Updated SMDR_PATTERN regex (line ~26-28)
   - Enhanced logging in parse_smdr_line (line ~96-115)
   - Added debug logging in _process_line (line ~228-245)

2. `snc-poc/pbx-connector/test_smdr_parser.py`
   - Added test_no_prefix_smdr_format test case

3. `snc-poc/pbx-connector/debug_smdr_records.py` (new)
   - Standalone test script for debugging

## Related Documentation

- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - System architecture
- [DEPLOYMENT_PI4.md](../DEPLOYMENT_PI4.md) - Deployment guide
- [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) - Common commands

---

**Date Fixed**: 2024-10-08  
**Issue**: Missing SMDR records without ==SMDX prefix  
**Status**: ✅ Resolved
