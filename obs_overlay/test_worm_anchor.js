// Test harness for worm ground anchor logic
console.log("Testing worm ground anchor logic...");

// Mock values from the actual code
const wormGroundMargin = 3;
const wormBaseScale = 1.08;

// Mock window.innerHeight
const mockWindowHeight = 800;

function wormGroundY() {
  return mockWindowHeight - wormGroundMargin; // 800 - 3 = 797
}

// Mock worm sprite with test values
let mockWormSprite = {
  opaqueBottomY: 100, // Example value - bottom of opaque pixels in sprite
  boneBaseY: 50,      // Example value - baseline of bones in sprite
  groundBaselineY(groundY, scale) {
    return groundY - (this.opaqueBottomY - this.boneBaseY) * scale;
  },
  poseDrawBounds(pose, scale) {
    // Simplified bounds calculation
    // For testing, assume the worm draws with its bottom at y + (opaqueBottomY - boneBaseY) * scale
    const bottomY = pose.y + (this.opaqueBottomY - this.boneBaseY) * scale;
    return {
      minX: pose.x,
      maxX: pose.x + 100 * scale, // arbitrary width
      minY: pose.y - 50 * scale,  // arbitrary height above baseline
      maxY: bottomY
    };
  },
  lengthAtScale(scale) {
    return 100 * scale; // arbitrary length
  }
};

// Test the groundBaselineY calculation
console.log("\n1. Testing groundBaselineY calculation:");
const groundY = wormGroundY(); // 797
const scale = wormBaseScale;   // 1.08
const baselineY = mockWormSprite.groundBaselineY(groundY, scale);
console.log(`groundY: ${groundY}`);
console.log(`scale: ${scale}`);
console.log(`opaqueBottomY: ${mockWormSprite.opaqueBottomY}`);
console.log(`boneBaseY: ${mockWormSprite.boneBaseY}`);
console.log(`opaqueBottomY - boneBaseY: ${mockWormSprite.opaqueBottomY - mockWormSprite.boneBaseY}`);
console.log(`(opaqueBottomY - boneBaseY) * scale: ${(mockWormSprite.opaqueBottomY - mockWormSprite.boneBaseY) * scale}`);
console.log(`groundBaselineY result: ${baselineY}`);

// Test anchorWormToGround logic
console.log("\n2. Testing anchorWormToGround logic:");

function wormPose(worm) {
  // Simplified pose calculation
  return {
    x: worm.x,
    y: worm.baselineY,
    scale: worm.scale,
    direction: worm.direction || 1
  };
}

function wormDrawBounds(worm) {
  const pose = wormPose(worm);
  return mockWormSprite.poseDrawBounds(pose, worm.scale);
}

function anchorWormToGround(worm) {
  worm.baselineY = mockWormSprite.groundBaselineY(wormGroundY(), worm.scale);
  const bounds = wormDrawBounds(worm);
  if (!Number.isFinite(bounds.maxY)) return;
  
  console.log(`  Initial baselineY: ${worm.baselineY}`);
  console.log(`  bounds.maxY: ${bounds.maxY}`);
  console.log(`  groundY: ${wormGroundY()}`);
  console.log(`  Adjustment (groundY - bounds.maxY): ${wormGroundY() - bounds.maxY}`);
  
  worm.baselineY += wormGroundY() - bounds.maxY;
  console.log(`  Final baselineY: ${worm.baselineY}`);
  
  // Verify
  const finalBounds = wormDrawBounds(worm);
  console.log(`  Final bounds.maxY: ${finalBounds.maxY}`);
  console.log(`  Should equal groundY (${wormGroundY()}): ${Math.abs(finalBounds.maxY - wormGroundY()) < 0.001 ? 'YES' : 'NO'}`);
}

// Test with a worm
const testWorm = {
  x: 100,
  baselineY: 0, // Will be set by anchorWormToGround
  scale: wormBaseScale,
  direction: 1
};

anchorWormToGround(testWorm);

// Test the actual bug: scale mismatch between groundBaselineY and pose
console.log("\n3. Testing scale mismatch bug:");

// Simulate the actual code: worm.scale grows, but pose uses wormRigScale
const wormRigScale = wormBaseScale; // 1.08

// Test with grown worm
console.log("\nCase: Worm has grown (scale = 1.42), but pose uses rig scale (1.08)");
const grownWormScale = 1.42; // wormMaxScale

// Current (buggy) implementation: groundBaselineY uses worm.scale (1.42)
// but pose uses wormRigScale (1.08)
function anchorWormToGroundBuggy(worm, useWormScaleInGroundBaseline = true) {
  const scaleForGroundBaseline = useWormScaleInGroundBaseline ? worm.scale : wormRigScale;
  worm.baselineY = mockWormSprite.groundBaselineY(wormGroundY(), scaleForGroundBaseline);
  const bounds = wormDrawBounds(worm);
  if (!Number.isFinite(bounds.maxY)) return;
  
  console.log(`  Using scale ${scaleForGroundBaseline} in groundBaselineY`);
  console.log(`  Initial baselineY: ${worm.baselineY}`);
  console.log(`  bounds.maxY: ${bounds.maxY}`);
  console.log(`  groundY: ${wormGroundY()}`);
  console.log(`  Adjustment (groundY - bounds.maxY): ${wormGroundY() - bounds.maxY}`);
  
  worm.baselineY += wormGroundY() - bounds.maxY;
  console.log(`  Final baselineY: ${worm.baselineY}`);
  
  // Verify
  const finalBounds = wormDrawBounds(worm);
  console.log(`  Final bounds.maxY: ${finalBounds.maxY}`);
  console.log(`  Should equal groundY (${wormGroundY()}): ${Math.abs(finalBounds.maxY - wormGroundY()) < 0.001 ? 'YES' : 'NO'}`);
}

const grownWorm = { x: 100, baselineY: 0, scale: grownWormScale, direction: 1 };
console.log("\nBuggy version (using worm.scale in groundBaselineY):");
anchorWormToGroundBuggy(grownWorm, true);

console.log("\nFixed version (using wormRigScale in groundBaselineY):");
const grownWorm2 = { x: 100, baselineY: 0, scale: grownWormScale, direction: 1 };
anchorWormToGroundBuggy(grownWorm2, false);

console.log("\n4. Analysis:");
console.log("The formula in anchorWormToGround is:");
console.log("  baselineY = groundBaselineY(groundY, scale) + (groundY - bounds.maxY)");
console.log("Where groundBaselineY(groundY, scale) = groundY - (opaqueBottomY - boneBaseY) * scale");
console.log("So: baselineY = groundY - (opaqueBottomY - boneBaseY) * scale + (groundY - bounds.maxY)");
console.log("   = 2*groundY - (opaqueBottomY - boneBaseY) * scale - bounds.maxY");
console.log("\nThis seems to double-count groundY. The adjustment should likely be:");
console.log("  baselineY = groundBaselineY(groundY, scale) - (bounds.maxY - groundY)");
console.log("Or equivalently:");
console.log("  baselineY = groundBaselineY(groundY, scale) + (groundY - bounds.maxY)");
console.log("Wait, that's the same... Let me think...");
console.log("\nActually, if bounds.maxY represents the actual drawn bottom,");
console.log("and we want bounds.maxY = groundY,");
console.log("then we need: baselineY = groundBaselineY(groundY, scale) + (groundY - bounds.maxY)");
console.log("This looks correct mathematically, but might have issues if bounds.maxY");
console.log("is calculated from a pose that uses the wrong baselineY.");