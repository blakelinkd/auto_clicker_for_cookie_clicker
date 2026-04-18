# Worm Ground Anchor Bug Analysis

## Problem
The worms ground anchor code is not keeping worms on the ground properly.

## Root Cause
Scale inconsistency between different parts of the worm rendering system:

1. **`worm.scale`** - Visual/grown scale (starts at 1.08, can grow up to 1.42 when eating)
2. **`wormRigScale`** - Bone rig scale (always fixed at 1.08 = `wormBaseScale`)

## Current Inconsistencies

### 1. `anchorWormToGround` function (line 2118-2123)
```javascript
function anchorWormToGround(worm) {
  worm.baselineY = wormSprite.groundBaselineY(wormGroundY(), wormRigScale);  // Uses wormRigScale
  const bounds = wormDrawBounds(worm);
  if (!Number.isFinite(bounds.maxY)) return;
  worm.baselineY += wormGroundY() - bounds.maxY;
}
```
**Fixed**: Changed from `worm.scale` to `wormRigScale` for consistency with pose building.

### 2. `wormPose` function (line 2138-2151)
```javascript
function wormPose(worm) {
  const visualScale = worm.scale || wormBaseScale;
  const poseScale = wormRigScale;  // Always uses wormRigScale, not worm.scale!
  // ...
  return wormSprite.buildInchwormPose({
    x: worm.x - facingOffset,
    y: worm.baselineY,
    scale: poseScale,  // Uses wormRigScale
    // ...
  });
}
```

### 3. `wormDrawBounds` function (line 2135-2137)
```javascript
function wormDrawBounds(worm) {
  return wormSprite.poseDrawBounds(wormPose(worm), worm.scale);  // Uses worm.scale
}
```

## The Bug
When a worm grows (`worm.scale` increases from 1.08 to up to 1.42):

1. `wormPose` builds the pose with `wormRigScale` (1.08)
2. `wormDrawBounds` calculates bounds with `worm.scale` (e.g., 1.42)
3. `poseDrawBounds` uses the scale parameter to calculate sprite bounds relative to bone points
4. Since the pose was built with scale 1.08 but bounds are calculated with scale 1.42, the bounds are incorrect
5. `anchorWormToGround` tries to adjust based on incorrect bounds

## Attempted Fixes

### Fix 1: Use consistent scale in `anchorWormToGround`
Changed line 2119 from `worm.scale` to `wormRigScale` to match `wormPose`.

**Status**: Applied

### Fix 2: Consider changing `wormPose` to use `worm.scale`
If worms should grow uniformly (bones and visual together), change line 2144:
```javascript
const poseScale = worm.scale || wormBaseScale;  // Instead of wormRigScale
```

**Status**: Not applied - would break facing offset calculation (line 2145)

### Fix 3: Consider changing `wormDrawBounds` to use `wormRigScale`
For consistency with pose building:
```javascript
return wormSprite.poseDrawBounds(wormPose(worm), wormRigScale);
```

**Status**: Not applied - would make bounds calculation use wrong visual scale

## The Core Design Issue
The system seems designed for:
- **Visual scale** (`worm.scale`): Controls how big the worm appears
- **Rig scale** (`wormRigScale`): Controls the bone structure scale (fixed)

But `poseDrawBounds` expects the visual scale to calculate proper bounds, while receiving a pose built with rig scale.

## Possible Solutions

### Solution A: Uniform scaling (Recommended)
Change `wormPose` to use `worm.scale` for pose scale:
```javascript
const poseScale = worm.scale || wormBaseScale;
```
And update facing offset calculation accordingly.

### Solution B: Separate scale parameters for `poseDrawBounds`
Modify `poseDrawBounds` to accept both rig scale and visual scale, or calculate bounds differently.

### Solution C: Keep current design but fix calculations
Ensure all calculations account for the difference between visual and rig scales consistently.

## Test Files Created
1. `test_worm_anchor.js` - Basic test harness
2. `test_worm_anchor2.js` - More accurate scale mismatch simulation

## Next Steps
1. Determine if worms should grow uniformly or keep fixed bone scale
2. Apply consistent scaling based on design decision
3. Test with actual overlay to verify worms stay on ground