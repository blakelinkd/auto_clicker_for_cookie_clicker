// More accurate test of the worm ground anchor bug
console.log("Testing worm ground anchor with scale mismatch...");

// Constants from actual code
const wormGroundMargin = 3;
const wormBaseScale = 1.08;
const wormRigScale = wormBaseScale;
const wormMaxScale = 1.42;

// Mock window
const mockWindowHeight = 800;

function wormGroundY() {
  return mockWindowHeight - wormGroundMargin; // 797
}

// Mock sprite with actual logic
let mockWormSprite = {
  opaqueBottomY: 100,
  boneBaseY: 50,
  restPoints: [{x: 0, y: 50}, {x: 100, y: 50}], // Simple rest points
  groundBaselineY(groundY, scale) {
    return groundY - (this.opaqueBottomY - this.boneBaseY) * scale;
  },
  buildInchwormPose(options) {
    // Simple pose: just returns the points
    const points = [];
    for (let i = 0; i < this.restPoints.length; i++) {
      points.push({
        x: options.x + this.restPoints[i].x * options.scale,
        y: options.y + this.restPoints[i].y * options.scale
      });
    }
    return points;
  },
  poseDrawBounds(pose, scale) {
    // Calculate bounds from pose points
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    for (let i = 0; i < pose.length - 1; i++) {
      const p0 = pose[i];
      const p1 = pose[i + 1];
      const sourceBoneY = this.restPoints[i].y;
      
      // Simplified: just use the points and account for sprite height
      const localBottom = (this.opaqueBottomY - sourceBoneY) * scale;
      const bottomY = p0.y + localBottom;
      
      minX = Math.min(minX, p0.x, p1.x);
      maxX = Math.max(maxX, p0.x, p1.x);
      minY = Math.min(minY, p0.y);
      maxY = Math.max(maxY, bottomY);
    }
    
    return { minX, maxX, minY, maxY };
  },
  lengthAtScale(scale) {
    return 100 * scale;
  }
};

// Simulate actual wormPose function
function wormPose(worm) {
  const visualScale = worm.scale || wormBaseScale;
  const poseScale = wormRigScale; // Always uses wormRigScale!
  const facingOffset = 0; // Simplified
  
  return mockWormSprite.buildInchwormPose({
    x: worm.x - facingOffset,
    y: worm.baselineY,
    scale: poseScale, // Uses wormRigScale, not worm.scale!
    direction: worm.direction || 1
  });
}

// Simulate actual wormDrawBounds
function wormDrawBounds(worm) {
  return mockWormSprite.poseDrawBounds(wormPose(worm), worm.scale); // Uses worm.scale for bounds!
}

// Current (buggy) anchorWormToGround
function anchorWormToGroundCurrent(worm) {
  // Uses worm.scale (visual/grown scale)
  worm.baselineY = mockWormSprite.groundBaselineY(wormGroundY(), worm.scale);
  const bounds = wormDrawBounds(worm);
  if (!Number.isFinite(bounds.maxY)) return;
  worm.baselineY += wormGroundY() - bounds.maxY;
}

// Fixed version: use wormRigScale in groundBaselineY
function anchorWormToGroundFixed(worm) {
  // Uses wormRigScale (pose scale)
  worm.baselineY = mockWormSprite.groundBaselineY(wormGroundY(), wormRigScale);
  const bounds = wormDrawBounds(worm);
  if (!Number.isFinite(bounds.maxY)) return;
  worm.baselineY += wormGroundY() - bounds.maxY;
}

// Test with base scale (1.08)
console.log("\n=== Test 1: Base scale worm (scale = 1.08) ===");
const baseWorm = { x: 100, baselineY: 0, scale: wormBaseScale, direction: 1 };

console.log("\nCurrent implementation:");
anchorWormToGroundCurrent(baseWorm);
console.log(`Final baselineY: ${baseWorm.baselineY}`);

const baseWorm2 = { x: 100, baselineY: 0, scale: wormBaseScale, direction: 1 };
console.log("\nFixed implementation:");
anchorWormToGroundFixed(baseWorm2);
console.log(`Final baselineY: ${baseWorm2.baselineY}`);

// Test with grown worm (1.42)
console.log("\n=== Test 2: Grown worm (scale = 1.42) ===");
const grownWorm = { x: 100, baselineY: 0, scale: wormMaxScale, direction: 1 };

console.log("\nCurrent implementation (BUGGY):");
console.log(`- groundBaselineY uses worm.scale (${grownWorm.scale})`);
console.log(`- wormPose uses poseScale (${wormRigScale})`);
console.log(`- wormDrawBounds uses worm.scale (${grownWorm.scale}) for bounds calculation`);
anchorWormToGroundCurrent(grownWorm);
const bounds1 = wormDrawBounds(grownWorm);
console.log(`Final baselineY: ${grownWorm.baselineY}`);
console.log(`Final bounds.maxY: ${bounds1.maxY}`);
console.log(`GroundY: ${wormGroundY()}`);
console.log(`Error: ${bounds1.maxY - wormGroundY()} pixels`);

const grownWorm2 = { x: 100, baselineY: 0, scale: wormMaxScale, direction: 1 };
console.log("\nFixed implementation:");
console.log(`- groundBaselineY uses wormRigScale (${wormRigScale})`);
console.log(`- wormPose uses poseScale (${wormRigScale})`);
console.log(`- wormDrawBounds uses worm.scale (${grownWorm2.scale}) for bounds calculation`);
anchorWormToGroundFixed(grownWorm2);
const bounds2 = wormDrawBounds(grownWorm2);
console.log(`Final baselineY: ${grownWorm2.baselineY}`);
console.log(`Final bounds.maxY: ${bounds2.maxY}`);
console.log(`GroundY: ${wormGroundY()}`);
console.log(`Error: ${bounds2.maxY - wormGroundY()} pixels`);

// The issue: In wormDrawBounds, poseDrawBounds is called with worm.scale (visual scale)
// but the pose was built with wormRigScale. So the bounds calculation uses the wrong scale!
// Actually, looking at poseDrawBounds implementation, it uses 'scale' parameter
// to calculate localBottom = (opaqueBottomY - sourceBoneY) * scale
// If scale is worm.scale (1.42) but pose was built with wormRigScale (1.08),
// the bounds will be wrong!

console.log("\n=== Analysis ===");
console.log("The real bug might be in wormDrawBounds:");
console.log("It calls: wormSprite.poseDrawBounds(wormPose(worm), worm.scale)");
console.log("But wormPose(worm) builds pose with wormRigScale,");
console.log("while poseDrawBounds uses worm.scale for bounds calculation.");
console.log("\nThis creates inconsistency: the pose points are scaled one way,");
console.log("but the bounds are calculated with a different scale.");