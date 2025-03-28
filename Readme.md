# Step-by-Step Guide to Finding Origin Location (One-Day Data)

## Step 1: Data Preprocessing

### 1. Filter Data for the Given Date
- Extract data for a specific date (e.g., `2025-03-22`).
- Ensure all records belong to this date before processing further.

### 2. Group Data by User (`user_id`)
- For each `user_id`, sort records by time (`start_time`, `hour`) to track movements.

### 3. Filter Only Relevant Columns
- Keep key attributes:
  - `user_id`, `h3_cell_id`, `latitude`, `longitude` (location info).
  - `stay_duration`, `start_time`, `end_time` (time-based info).
  - `h3_cell_id_7` (for clustering small regions into a larger area).

---

## Step 2: Identify Stay Locations

### 1. Define Stay Location Criteria
- A stay location is where a person remains for **≥ 6 hours** (`stay_duration >= 6 hours`).
- If a user has multiple such locations, proceed to Step 3.

### 2. Identify the First Stay Location
- Check if the user was already at a place from **12 AM - 6 AM** and stayed for a long time.
- If this condition is met, mark it as the origin.

### 3. If No Stay Location Meets the 6-Hour Threshold:
- Find the longest stay duration from available locations.
- If multiple locations have equal stay duration, move to Step 3.

---

## Step 3: Resolving Multiple Stay Locations

If a user has more than one stay location:

### 1. Compare Stay Durations
- Select the location with the **longest stay**.

### 2. Use `h3_cell_id_7` for Clustering
- If multiple `h3_cell_id` values exist within the same `h3_cell_id_7`, consider them as one broader stay location.

### 3. Check Movement Patterns Before Arrival at `place_id`
- If a person moves frequently between multiple places, the location with the **most continuous stay** before movement is the origin.

### 4. Use First Arrival Time as a Tie-Breaker
- If two locations have similar durations, choose the **earliest visited** as the origin.

---

## Step 4: Handling Special Cases

✅ **Case 1: Origin and `place_id` Are the Same**
- If a person’s origin and the place they visit frequently (`place_id`) are the same:
  - Check if they frequently move back and forth → Suggests they **live and work nearby**.

✅ **Case 2: A Person Has No Long Stay (Moving Constantly)**
- If no stay location meets the threshold:
  - Look for the **first place with a stay of at least 3-4 hours**.
  - If still no match, choose the **first recorded location**.

✅ **Case 3: A Person Has Two Equal Stay Durations**
- Check which location they **visited earlier in the day**.
- If both are visited at the same time, choose the one they **returned to more frequently**.

✅ **Case 4: A Person Has a Short Stay at Night but Long Stay During the Day**
- If they stay at a place for **4-5 hours at night** (e.g., `12 AM - 6 AM`) but longer elsewhere during the day:
  - Consider the night location as a **possible home** but validate against duration.

✅ **Case 5: A Person is Detected in Multiple Nearby H3 Cells**
- If their `h3_cell_id` changes slightly but stays within the same `h3_cell_id_7`, count it as **one location**.

---

## Step 5: Additional Ways to Improve Accuracy

✅ **Use Latitude & Longitude Clustering**
- If two locations have slightly different `h3_cell_id` values but are geographically close, merge them.

✅ **Detect Frequent Work-Home Commutes**
- If a person moves between two places frequently within one day, classify them as a **home-work pattern**.

✅ **Check if Users Return to a Place Frequently**
- If a person returns to a location **more than once**, that place is likely important (**home or work**).

✅ **Use Probability Models**
- If a person has two possible origins, assign a probability:
  - **Night Stay**: 70% chance of being home.
  - **Longest Stay**: 30% chance of being home.

---

## Final Decision: Selecting the Best Origin Location

After processing all steps, determine the origin using the following priority order:

1️⃣ **Longest Stay Location** (if unique).
2️⃣ **Stay Location from 12 AM - 6 AM** (if duration is sufficient).
3️⃣ **Most Visited Stay Location** (Clustered by `h3_cell_id_7`).
4️⃣ **First Recorded Stay Location of the Day** (if multiple exist).

