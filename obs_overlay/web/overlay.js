(() => {
  "use strict";

  const canvas = document.getElementById("overlay");
  const ctx = canvas.getContext("2d");
  const config = Object.assign({ snakeEnabled: true }, window.OVERLAY_CONFIG || {});
  const assetVersion = "snake-heat-7";
  const bidenSprite = new Image();
  const grandmaHeadSprite = new Image();
  const sounds = {
    dean: createAudioPool(`/assets/audio/dean_scream.mp3?v=${assetVersion}`, 0.65, 3),
    grandma: createAudioPool(`/assets/audio/grandma_cookie.mp3?v=${assetVersion}`, 0.45, 4),
  };
  const bidenSpawns = [];
  const bidenSpawnByShimmerId = new Map();

  const fingerAnchor = { x: 0.0071, y: 0.1389 };
  const defaultBidenHeight = 320;
  const snakeHeadDrawSize = 86;
  const snakeBodyDrawSize = 78;
  const cellSize = 68;
  const snakeTickMs = 230;
  const snake = {
    mode: "snake",
    segments: [],
    previousSegments: [],
    heatSegments: [],
    heatDirection: { x: 1, y: 0 },
    direction: { x: 1, y: 0 },
    grow: 0,
    lastTick: 0,
    lastFrame: 0,
    moveStartedAt: 0,
    scanRow: 0,
    scanDirection: 1,
    eatenCount: 0,
  };
  const combatLog = [];
  let lastDurgularYell = 0;
  let bidenSpawnCount = 0;
  const biotachyonicWhisper = "it's supposed to look like biden is popping the cookies...";
  const bidenFocusLines = [
    "Oh, it's focused.",
    "I'd say it's... I think it's...",
    "I have trouble even mentioning the number of years.",
    "I don't think of myself that way.",
    "I haven't noticed things I can't do.",
    "Physical, mental, anything else.",
  ];
  const durgularLines = [
    "DURGULAAAAAR!",
    "DURGULAR!!",
    "DURGULAAAAAAAAAR!!!",
    "DUR-GU-LAR!",
    "DURGULAAAAAR!!!!",
  ];

  bidenSprite.src = "/assets/biden_i_did_that.png";
  grandmaHeadSprite.src = `/assets/game/grandma_head_smooth.png?v=${assetVersion}`;

  function createAudioPool(src, volume, count) {
    const clips = [];
    for (let i = 0; i < count; i += 1) {
      const audio = new Audio(src);
      audio.preload = "auto";
      audio.volume = volume;
      audio.muted = false;
      audio.setAttribute("playsinline", "");
      audio.style.display = "none";
      document.body.appendChild(audio);
      audio.load();
      clips.push(audio);
    }
    return { clips, next: 0 };
  }

  function playSound(pool) {
    if (!pool || pool.clips.length === 0) return;
    const audio = pool.clips[pool.next];
    pool.next = (pool.next + 1) % pool.clips.length;
    try {
      audio.pause();
      audio.currentTime = 0;
      const result = audio.play();
      if (result && typeof result.catch === "function") {
        result.catch((error) => {
          console.warn("Overlay audio playback was blocked or failed.", error);
        });
      }
    } catch (error) {
      console.warn("Overlay audio playback was blocked or failed.", error);
    }
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, Number(value)));
  }

  function gridWidth() {
    return Math.max(1, Math.floor(window.innerWidth / cellSize));
  }

  function gridHeight() {
    return Math.max(1, Math.floor(window.innerHeight / cellSize));
  }

  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(window.innerWidth));
    const height = Math.max(1, Math.round(window.innerHeight));
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    refreshBidenCells();
    if (snake.mode === "heat") {
      clampHeatSegmentsToViewport();
      return;
    }
    if (snake.segments.length === 0 || snake.segments.some((segment) => !isInBounds(segment))) {
      resetSnake();
    }
  }

  function resetSnake() {
    const head = {
      x: Math.floor(gridWidth() / 2),
      y: Math.floor(gridHeight() / 2),
    };
    snake.segments = [head];
    snake.previousSegments = [head];
    snake.heatSegments = gridSegmentsToPixels(snake.segments);
    snake.heatDirection = { x: 1, y: 0 };
    snake.direction = { x: 1, y: 0 };
    snake.grow = 0;
    snake.scanRow = Math.floor(gridHeight() / 2);
    snake.scanDirection = 1;
    snake.lastTick = performance.now();
    snake.lastFrame = snake.lastTick;
    snake.moveStartedAt = snake.lastTick;
  }

  function cloneSegments(segments) {
    return segments.map((segment) => ({ x: segment.x, y: segment.y }));
  }

  function targetToCell(normX, normY) {
    return {
      x: Math.max(0, Math.min(gridWidth() - 1, Math.round(normX * (gridWidth() - 1)))),
      y: Math.max(0, Math.min(gridHeight() - 1, Math.round(normY * (gridHeight() - 1)))),
    };
  }

  function cellToPixel(cell) {
    const width = gridWidth();
    const height = gridHeight();
    const offsetX = (window.innerWidth - width * cellSize) / 2;
    const offsetY = (window.innerHeight - height * cellSize) / 2;
    return {
      x: offsetX + cell.x * cellSize + cellSize / 2,
      y: offsetY + cell.y * cellSize + cellSize / 2,
    };
  }

  function pixelToCell(point) {
    const width = gridWidth();
    const height = gridHeight();
    const offsetX = (window.innerWidth - width * cellSize) / 2;
    const offsetY = (window.innerHeight - height * cellSize) / 2;
    return {
      x: Math.max(0, Math.min(width - 1, Math.round((point.x - offsetX - cellSize / 2) / cellSize))),
      y: Math.max(0, Math.min(height - 1, Math.round((point.y - offsetY - cellSize / 2) / cellSize))),
    };
  }

  function gridSegmentsToPixels(segments) {
    return segments.map((segment) => cellToPixel(segment));
  }

  function clampHeatSegmentsToViewport() {
    const margin = snakeHeadDrawSize / 2;
    for (const segment of snake.heatSegments) {
      segment.x = Math.max(margin, Math.min(window.innerWidth - margin, segment.x));
      segment.y = Math.max(margin, Math.min(window.innerHeight - margin, segment.y));
    }
  }

  function addBidenSpawn(payload) {
    const target = payload.target || {};
    const normX = clamp01(target.norm_x);
    const normY = clamp01(target.norm_y);
    if (!Number.isFinite(normX) || !Number.isFinite(normY)) return false;
    const shimmerId = payload.shimmer && payload.shimmer.id != null ? String(payload.shimmer.id) : null;
    const existingSpawn = shimmerId !== null ? bidenSpawnByShimmerId.get(shimmerId) : null;
    if (existingSpawn) {
      existingSpawn.normX = normX;
      existingSpawn.normY = normY;
      existingSpawn.cell = targetToCell(normX, normY);
      existingSpawn.startedAt = performance.now();
      existingSpawn.eventId = payload.event_id || existingSpawn.eventId || null;
      existingSpawn.mode = payload.mode || existingSpawn.mode || null;
      existingSpawn.beingEaten = false;
      existingSpawn.eatenAt = null;
      return true;
    }

    const spawn = {
      normX,
      normY,
      cell: targetToCell(normX, normY),
      startedAt: performance.now(),
      shimmerId,
      eventId: payload.event_id || null,
      mode: payload.mode || null,
      beingEaten: false,
      eatenAt: null,
    };
    bidenSpawns.push(spawn);
    if (shimmerId !== null) {
      bidenSpawnByShimmerId.set(shimmerId, spawn);
    }
    const now = spawn.startedAt;
    bidenSpawnCount += 1;
    queueBidenFocusTalk(now);
    if (bidenSpawnCount % 10 === 0) {
      addCombatLogLine("biotachyonic", biotachyonicWhisper, now + 350, "whisper");
    }
    playSound(sounds.dean);
    return true;
  }

  function queueBidenFocusTalk(now) {
    let lineAt = now;
    for (let i = 0; i < bidenFocusLines.length; i += 1) {
      addCombatLogLine("biden", bidenFocusLines[i], lineAt);
      lineAt += 1000 + Math.random() * 1000;
    }
  }

  function maybeAddDurgularYell(now) {
    if (lastDurgularYell === 0) {
      lastDurgularYell = now;
      return;
    }
    if (now - lastDurgularYell < 20000) return;
    const index = Math.floor(now / 20000) % durgularLines.length;
    addCombatLogLine("durgular", durgularLines[index], now);
    lastDurgularYell = now;
  }

  function refreshBidenCells() {
    for (const spawn of bidenSpawns) {
      spawn.cell = targetToCell(spawn.normX, spawn.normY);
    }
  }

  function addSpawn(payload) {
    if (!payload) return;
    if (payload.type === "spawn_biden") {
      addBidenSpawn(payload);
      return;
    }
    if (payload.type === "play_sound") {
      if (payload.sound === "dean") playSound(sounds.dean);
      if (payload.sound === "grandma") playSound(sounds.grandma);
    }
  }

  function isInBounds(point) {
    return point.x >= 0 && point.x < gridWidth() && point.y >= 0 && point.y < gridHeight();
  }

  function sameCell(a, b) {
    return a && b && a.x === b.x && a.y === b.y;
  }

  function snakeOccupies(cell, includeTail) {
    const limit = includeTail ? snake.segments.length : Math.max(0, snake.segments.length - 1);
    for (let i = 0; i < limit; i += 1) {
      if (sameCell(snake.segments[i], cell)) return true;
    }
    return false;
  }

  function gridDistance(a, b) {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
  }

  function pixelDistance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function bidenCenter(spawn) {
    return {
      x: spawn.normX * window.innerWidth,
      y: spawn.normY * window.innerHeight,
    };
  }

  function activeBidenSpawns() {
    return bidenSpawns.filter((spawn) => !spawn.beingEaten);
  }

  function nearestTarget(head) {
    const activeBidens = activeBidenSpawns();
    if (activeBidens.length > 0) {
      let best = activeBidens[0];
      let bestDistance = gridDistance(head, best.cell);
      for (let i = 1; i < activeBidens.length; i += 1) {
        const distance = gridDistance(head, activeBidens[i].cell);
        if (distance < bestDistance) {
          best = activeBidens[i];
          bestDistance = distance;
        }
      }
      return best;
    }

    return patrolTarget(head);
  }

  function patrolTarget(head) {
    const width = gridWidth();
    const height = gridHeight();
    if (head.y === snake.scanRow) {
      const atRowEnd = snake.scanDirection > 0 ? head.x >= width - 1 : head.x <= 0;
      if (atRowEnd) {
        snake.scanRow = (snake.scanRow + 1) % height;
        snake.scanDirection *= -1;
      }
    }

    return {
      cell: {
        x: snake.scanDirection > 0 ? width - 1 : 0,
        y: snake.scanRow,
      },
      isPatrol: true,
    };
  }

  function addCombatLogLine(speaker, text, now, channel = "say") {
    combatLog.push({ speaker, text, startedAt: now, channel });
    while (combatLog.length > 18) {
      combatLog.shift();
    }
  }

  function handleBidenEaten(spawn, now) {
    spawn.beingEaten = true;
    spawn.eatenAt = now;
    snake.eatenCount += 1;
    playSound(sounds.grandma);
    if (snake.eatenCount % 3 === 0) {
      toggleGrandmaMode(now);
    }
  }

  function toggleGrandmaMode(now) {
    if (snake.mode === "snake") {
      enterHeatSeekingMode(now);
      addCombatLogLine("grandma", "Heat seeking mode engage!", now);
      return;
    }
    enterSnakeMode(now);
    addCombatLogLine("grandma", "I'm a snaaake.", now);
  }

  function enterHeatSeekingMode(now) {
    snake.mode = "heat";
    snake.heatSegments = gridSegmentsToPixels(interpolatedSegments(now));
    if (snake.heatSegments.length === 0) {
      snake.heatSegments = gridSegmentsToPixels(snake.segments);
    }
    snake.heatDirection = { x: snake.direction.x, y: snake.direction.y };
    snake.lastFrame = now;
  }

  function enterSnakeMode(now) {
    snake.mode = "snake";
    const head = pixelToCell(snake.heatSegments[0] || cellToPixel(snake.segments[0]));
    const targetLength = Math.max(1, snake.heatSegments.length, snake.segments.length);
    const direction = dominantGridDirection(snake.heatDirection);
    snake.segments = buildGridSegments(head, direction, targetLength);
    snake.previousSegments = cloneSegments(snake.segments);
    snake.direction = direction;
    snake.grow = 0;
    snake.lastTick = now;
    snake.moveStartedAt = now;
  }

  function dominantGridDirection(vector) {
    if (Math.abs(vector.x) >= Math.abs(vector.y)) {
      return { x: vector.x >= 0 ? 1 : -1, y: 0 };
    }
    return { x: 0, y: vector.y >= 0 ? 1 : -1 };
  }

  function buildGridSegments(head, direction, targetLength) {
    const segments = [head];
    const attempts = [
      { x: -direction.x, y: -direction.y },
      { x: -direction.y, y: direction.x },
      { x: direction.y, y: -direction.x },
      { x: direction.x, y: direction.y },
    ];

    for (let i = 1; i < targetLength; i += 1) {
      let placed = false;
      for (const attempt of attempts) {
        const cell = { x: head.x + attempt.x * i, y: head.y + attempt.y * i };
        if (isInBounds(cell) && !segments.some((segment) => sameCell(segment, cell))) {
          segments.push(cell);
          placed = true;
          break;
        }
      }
      if (!placed) {
        segments.push({
          x: head.x + attempts[0].x * i,
          y: head.y + attempts[0].y * i,
        });
      }
    }
    return segments;
  }

  function candidateDirections(head, target) {
    const directions = [
      { x: 1, y: 0 },
      { x: -1, y: 0 },
      { x: 0, y: 1 },
      { x: 0, y: -1 },
    ];
    const candidates = directions.map((direction) => {
      const next = { x: head.x + direction.x, y: head.y + direction.y };
      const outOfBounds = !isInBounds(next);
      const isBackwards = direction.x === -snake.direction.x && direction.y === -snake.direction.y;
      return {
        direction,
        next,
        distance: target ? gridDistance(next, target.cell) : 0,
        blocked: outOfBounds || snakeOccupies(next, snake.grow > 0),
        isBackwards: isBackwards && snake.segments.length > 1,
      };
    });
    
    const nonBackwardsCandidates = candidates.filter(c => !c.isBackwards);
    const unblockedNonBackwards = nonBackwardsCandidates.filter(c => !c.blocked);
    
    if (unblockedNonBackwards.length > 0) {
      if (target) {
        return unblockedNonBackwards.sort((a, b) => a.distance - b.distance);
      } else {
        return unblockedNonBackwards.sort(() => Math.random() - 0.5);
      }
    }
    
    const backwardsCandidate = candidates.find(c => c.isBackwards);
    if (backwardsCandidate && !backwardsCandidate.blocked) {
      return [backwardsCandidate];
    }
    
    return candidates.sort((a, b) => {
      if (a.blocked !== b.blocked) return a.blocked ? 1 : -1;
      return a.distance - b.distance;
    });
  }

  function advanceSnake(now) {
    if (!config.snakeEnabled) return;
    if (snake.mode === "heat") {
      advanceHeatSeeking(now);
      return;
    }
    advanceGridSnake(now);
  }

  function advanceGridSnake(now) {
    
    if (snake.segments.length === 0) resetSnake();
    if (!isInBounds(snake.segments[0])) {
      resetSnake();
    }
    if (now - snake.lastTick < snakeTickMs) return;
    snake.lastTick = now;

    const head = snake.segments[0];
    const target = nearestTarget(head);
    const candidates = candidateDirections(head, target);
    const chosen = candidates.find((candidate) => !candidate.blocked);
    if (!chosen) {
      resetSnake();
      return;
    }

    snake.direction = chosen.direction;
    const nextHead = chosen.next;
    if (!isInBounds(nextHead) || snakeOccupies(nextHead, snake.grow > 0)) {
      resetSnake();
      return;
    }

    snake.previousSegments = cloneSegments(snake.segments);
    snake.segments.unshift(nextHead);
    const bidenSpawn = bidenSpawns.find((spawn) => spawn.cell && sameCell(spawn.cell, nextHead));
    if (bidenSpawn) {
      snake.grow += 1;
    }

    if (snake.grow > 0) {
      snake.grow -= 1;
      const tail = snake.segments[snake.segments.length - 1];
      if (tail) {
        snake.segments.push({ x: tail.x, y: tail.y });
      }
    } else {
      snake.segments.pop();
    }
    snake.moveStartedAt = now;
    if (bidenSpawn) {
      handleBidenEaten(bidenSpawn, now);
    }
  }

  function advanceHeatSeeking(now) {
    if (snake.heatSegments.length === 0) {
      snake.heatSegments = gridSegmentsToPixels(interpolatedSegments(now));
    }

    const dt = Math.min(80, Math.max(0, now - (snake.lastFrame || now)));
    snake.lastFrame = now;
    const head = snake.heatSegments[0];
    const target = nearestHeatTarget(head);
    const speed = cellSize / snakeTickMs;
    const maxStep = speed * dt;
    let desired = target
      ? vectorToward(head, bidenCenter(target))
      : snake.heatDirection;

    if (!target) {
      desired = bounceHeatDirection(head, desired);
    }

    snake.heatDirection = desired;
    head.x += desired.x * maxStep;
    head.y += desired.y * maxStep;
    clampHeatSegmentsToViewport();

    if (target && pixelDistance(head, bidenCenter(target)) <= cellSize * 0.55) {
      const tail = snake.heatSegments[snake.heatSegments.length - 1] || head;
      snake.heatSegments.push({ x: tail.x, y: tail.y });
      handleBidenEaten(target, now);
    }

    relaxHeatTail();
  }

  function nearestHeatTarget(head) {
    const activeBidens = activeBidenSpawns();
    if (activeBidens.length === 0) return null;
    let best = activeBidens[0];
    let bestDistance = pixelDistance(head, bidenCenter(best));
    for (let i = 1; i < activeBidens.length; i += 1) {
      const distance = pixelDistance(head, bidenCenter(activeBidens[i]));
      if (distance < bestDistance) {
        best = activeBidens[i];
        bestDistance = distance;
      }
    }
    return best;
  }

  function vectorToward(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance <= 0.001) return snake.heatDirection;
    return { x: dx / distance, y: dy / distance };
  }

  function bounceHeatDirection(head, direction) {
    const margin = snakeHeadDrawSize / 2;
    let next = { x: direction.x, y: direction.y };
    if (head.x <= margin || head.x >= window.innerWidth - margin) {
      next.x *= -1;
    }
    if (head.y <= margin || head.y >= window.innerHeight - margin) {
      next.y *= -1;
    }
    const length = Math.sqrt(next.x * next.x + next.y * next.y);
    return length > 0.001 ? { x: next.x / length, y: next.y / length } : { x: 1, y: 0 };
  }

  function relaxHeatTail() {
    const spacing = cellSize * 0.85;
    for (let i = 1; i < snake.heatSegments.length; i += 1) {
      const leader = snake.heatSegments[i - 1];
      const follower = snake.heatSegments[i];
      const dx = follower.x - leader.x;
      const dy = follower.y - leader.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance > spacing && distance > 0.001) {
        follower.x = leader.x + (dx / distance) * spacing;
        follower.y = leader.y + (dy / distance) * spacing;
      }
    }
  }

  function interpolatedSegments(now) {
    const elapsed = Math.max(0, now - snake.moveStartedAt);
    const t = Math.min(1, elapsed / snakeTickMs);
    return snake.segments.map((segment, index) => {
      const previous = snake.previousSegments[index]
        || snake.previousSegments[snake.previousSegments.length - 1]
        || segment;
      return {
        x: previous.x + (segment.x - previous.x) * t,
        y: previous.y + (segment.y - previous.y) * t,
      };
    });
  }

  function drawSnake(now) {
    if (!config.snakeEnabled) return;
    if (!grandmaHeadSprite.complete || !grandmaHeadSprite.naturalWidth || !grandmaHeadSprite.naturalHeight) return;
    if (snake.mode === "heat") {
      drawHeatSeekingSnake(now);
      return;
    }
    
      const scale = 1;
      const width = gridWidth();
      const height = gridHeight();
      const offsetX = (window.innerWidth - width * cellSize) / 2;
      const offsetY = (window.innerHeight - height * cellSize) / 2;
      const visualSegments = interpolatedSegments(now);

      // Compute sizes for each segment with 4% shrinkage/grow-back
      const sizes = [];
      let multiplier = 1;
      let direction = -1; // -1 = shrinking, 1 = growing
      const shrinkFactor = 0.96;
      const growFactor = 1.04;
      const minThreshold = 0.4; // start growing when too small (increased from 0.15)
      const maxThreshold = 1.0; // start shrinking when back to full size
      
      for (let i = 0; i < visualSegments.length; i++) {
        sizes.push(multiplier);
        // Update multiplier for next segment
        if (direction === -1) {
          multiplier *= shrinkFactor;
          if (multiplier < minThreshold) {
            direction = 1;
            multiplier = minThreshold * growFactor; // start growing
          }
        } else {
          multiplier *= growFactor;
          if (multiplier > maxThreshold) {
            direction = -1;
            multiplier = maxThreshold * shrinkFactor; // start shrinking
          }
        }
      }
      
      // Draw segments from tail to head (so head draws on top)
      for (let i = visualSegments.length - 1; i >= 0; i -= 1) {
        const segment = visualSegments[i];
        const isHead = i === 0;
        const prevSegment = i > 0 ? visualSegments[i - 1] : null;
        
        // Base grid position
        let x = offsetX + segment.x * cellSize;
        let y = offsetY + segment.y * cellSize;
        
        // Add visual offset for trailing effect in hunt mode
        if (!isHead && prevSegment) {
          // Calculate direction from this segment to previous one (where snake is moving)
          const dx = prevSegment.x - segment.x;
          const dy = prevSegment.y - segment.y;
          
          // Offset in the opposite direction of movement to create trailing gap
          const trailOffset = cellSize * 0.15 * Math.max(0.45, sizes[i]);
          x += dx * trailOffset;
          y += dy * trailOffset;
        }
        
        const baseSize = isHead ? snakeHeadDrawSize : snakeBodyDrawSize;
        const size = baseSize * scale * sizes[i];
        const bob = isHead ? Math.sin(performance.now() / 140) * 2 : 0;

        ctx.save();
        ctx.translate(x + cellSize / 2, y + cellSize / 2 + bob);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(grandmaHeadSprite, -size / 2, -size / 2, size, size);
        ctx.restore();
      }
  }

  function drawHeatSeekingSnake(now) {
    const sizes = segmentSizeMultipliers(snake.heatSegments.length);
    for (let i = snake.heatSegments.length - 1; i >= 0; i -= 1) {
      const segment = snake.heatSegments[i];
      const isHead = i === 0;
      const baseSize = isHead ? snakeHeadDrawSize : snakeBodyDrawSize;
      const size = baseSize * sizes[i];
      const bob = isHead ? Math.sin(now / 140) * 2 : 0;

      ctx.save();
      ctx.translate(segment.x, segment.y + bob);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(grandmaHeadSprite, -size / 2, -size / 2, size, size);
      ctx.restore();
    }
  }

  function segmentSizeMultipliers(count) {
    const sizes = [];
    let multiplier = 1;
    let direction = -1;
    const shrinkFactor = 0.96;
    const growFactor = 1.04;
    const minThreshold = 0.4;
    const maxThreshold = 1.0;

    for (let i = 0; i < count; i += 1) {
      sizes.push(multiplier);
      if (direction === -1) {
        multiplier *= shrinkFactor;
        if (multiplier < minThreshold) {
          direction = 1;
          multiplier = minThreshold * growFactor;
        }
      } else {
        multiplier *= growFactor;
        if (multiplier > maxThreshold) {
          direction = -1;
          multiplier = maxThreshold * shrinkFactor;
        }
      }
    }
    return sizes;
  }

  function drawBidens(now) {
    const gridHead = snake.segments.length > 0 ? snake.segments[0] : null;
    const heatHead = snake.heatSegments.length > 0 ? snake.heatSegments[0] : null;
    
    for (let i = bidenSpawns.length - 1; i >= 0; i -= 1) {
      const spawn = bidenSpawns[i];
      
      let distance = 999;
      if (snake.mode === "heat" && heatHead) {
        distance = pixelDistance(heatHead, bidenCenter(spawn)) / cellSize;
      } else if (gridHead && spawn.cell) {
        distance = gridDistance(gridHead, spawn.cell);
      }
      
      // Proximity-based behavior
      const proximityFactor = Math.max(0, 1 - (distance / 10)); // 0 = far, 1 = adjacent
      
      // Being eaten animation
      if (spawn.beingEaten && spawn.eatenAt) {
        const eatProgress = Math.max(0, Math.min(1, (now - spawn.eatenAt) / 400));
        if (eatProgress >= 1) {
          if (spawn.shimmerId !== null) {
            bidenSpawnByShimmerId.delete(spawn.shimmerId);
          }
          bidenSpawns.splice(i, 1);
          continue;
        }
        const scale = 1 - (0.45 * eatProgress);
        const opacity = 1 - eatProgress;
        drawBidenSprite(spawn, scale, opacity, now, proximityFactor);
        continue;
      }
      
      // Normal biden - proximity-based shrink and wiggle
      if (!bidenSprite.complete || !bidenSprite.naturalWidth || !bidenSprite.naturalHeight) continue;
      
      // Shrink based on proximity (closer = more shrunk)
      const shrinkFactor = proximityFactor * 0.6;
      const scale = 1 - shrinkFactor;
      const opacity = 1 - (shrinkFactor * 0.3);
      
      drawBidenSprite(spawn, scale, opacity, now, proximityFactor);
    }
  }

  function drawBidenSprite(spawn, scale, opacity, now, proximityFactor) {
    const baseHeight = defaultBidenHeight;
    const baseWidth = bidenSprite.naturalWidth * (baseHeight / bidenSprite.naturalHeight);
    const drawWidth = baseWidth * scale;
    const drawHeight = baseHeight * scale;
    let targetX = spawn.normX * window.innerWidth;
    let targetY = spawn.normY * window.innerHeight;
    
    // Frantic wiggle based on proximity
    const wiggleIntensity = proximityFactor * 15;
    const wiggleSpeed = 50 + (proximityFactor * 100); // faster when closer
    const wiggle = Math.sin(now / wiggleSpeed) * wiggleIntensity;
    targetX += wiggle;
    
    const drawX = targetX - (drawWidth * fingerAnchor.x);
    const drawY = targetY - (drawHeight * fingerAnchor.y);

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(bidenSprite, drawX, drawY, drawWidth, drawHeight);
    ctx.restore();
  }

  function drawCombatLog(now) {
    const baseWidth = Math.max(260, Math.min(420, window.innerWidth / 6));
    const width = Math.min(window.innerWidth - 36, baseWidth * 1.4);
    const fontSize = 14;
    const lineHeight = 20;
    const padding = 11;
    const fadeHeight = 30;
    const height = Math.min(window.innerHeight - 36, (padding * 2 + lineHeight * 5) * 2.7);
    const x = window.innerWidth - width - 18;
    const y = window.innerHeight - height - 18;
    const contentX = x + padding;
    const contentY = y + padding;
    const contentWidth = width - padding * 2;
    const contentHeight = height - padding * 2;

    ctx.save();
    ctx.fillStyle = "rgba(8, 10, 12, 0.62)";
    ctx.strokeStyle = "rgba(214, 173, 82, 0.65)";
    ctx.lineWidth = 1;
    ctx.fillRect(x, y, width, height);
    ctx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);

    ctx.font = `600 ${fontSize}px Verdana, Geneva, sans-serif`;
    ctx.textBaseline = "top";
    ctx.shadowColor = "rgba(0, 0, 0, 0.95)";
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;

    const wrappedLines = layoutCombatLogLines(
      combatLog.filter((entry) => entry.startedAt <= now),
      contentWidth
    );
    const maxLineCount = Math.floor(contentHeight / lineHeight);
    const visibleLines = wrappedLines.slice(-maxLineCount);
    let lineY = contentY + contentHeight - visibleLines.length * lineHeight;

    ctx.save();
    ctx.beginPath();
    ctx.rect(contentX, contentY, contentWidth, contentHeight);
    ctx.clip();

    for (const line of visibleLines) {
      const age = Math.max(0, now - line.startedAt);
      const alpha = Math.max(0.62, Math.min(1, 1 - age / 30000));
      if (line.showSpeaker) {
        ctx.font = `600 ${fontSize}px Verdana, Geneva, sans-serif`;
        ctx.fillStyle = speakerColor(line.speaker, alpha);
        ctx.fillText(line.speakerLabel, contentX, lineY, contentWidth);
      }
      ctx.font = messageFont(line.channel, fontSize);
      ctx.fillStyle = messageColor(line.channel, alpha);
      ctx.fillText(line.text, contentX + line.textOffset, lineY, contentWidth - line.textOffset);
      lineY += lineHeight;
    }
    ctx.restore();

    const fade = ctx.createLinearGradient(0, contentY, 0, contentY + fadeHeight);
    fade.addColorStop(0, "rgba(8, 10, 12, 0.92)");
    fade.addColorStop(1, "rgba(8, 10, 12, 0)");
    ctx.shadowColor = "transparent";
    ctx.fillStyle = fade;
    ctx.fillRect(contentX, contentY, contentWidth, fadeHeight);
    ctx.restore();
  }

  function layoutCombatLogLines(entries, maxWidth) {
    const lines = [];
    for (const entry of entries) {
      const speakerLabel = `${entry.speaker}: `;
      const speakerWidth = ctx.measureText(speakerLabel).width;
      const words = entry.text.split(/\s+/).filter(Boolean);
      let current = "";
      let showSpeaker = true;
      let textOffset = speakerWidth;
      let availableWidth = Math.max(40, maxWidth - textOffset);

      for (const word of words) {
        const candidate = current ? `${current} ${word}` : word;
        if (!current && ctx.measureText(candidate).width > availableWidth) {
          const chunks = splitLongWord(candidate, availableWidth);
          for (let i = 0; i < chunks.length - 1; i += 1) {
            lines.push({
              speaker: entry.speaker,
              speakerLabel,
              text: chunks[i],
              textOffset,
              showSpeaker,
              startedAt: entry.startedAt,
              channel: entry.channel,
            });
            showSpeaker = false;
            textOffset = 18;
            availableWidth = Math.max(40, maxWidth - textOffset);
          }
          current = chunks[chunks.length - 1] || "";
          continue;
        }
        if (ctx.measureText(candidate).width <= availableWidth || !current) {
          current = candidate;
          continue;
        }

        lines.push({
          speaker: entry.speaker,
          speakerLabel,
          text: current,
          textOffset,
          showSpeaker,
          startedAt: entry.startedAt,
          channel: entry.channel,
        });
        current = word;
        showSpeaker = false;
        textOffset = 18;
        availableWidth = Math.max(40, maxWidth - textOffset);
      }

      lines.push({
        speaker: entry.speaker,
        speakerLabel,
        text: current,
        textOffset,
        showSpeaker,
        startedAt: entry.startedAt,
        channel: entry.channel,
      });
    }
    return lines;
  }

  function speakerColor(speaker, alpha) {
    if (speaker === "biden") return `rgba(170, 211, 114, ${alpha})`;
    if (speaker === "durgular") return `rgba(198, 155, 109, ${alpha})`;
    if (speaker === "biotachyonic") return `rgba(255, 124, 10, ${alpha})`;
    return `rgba(135, 136, 238, ${alpha})`;
  }

  function messageColor(channel, alpha) {
    if (channel === "whisper") return `rgba(255, 128, 255, ${alpha})`;
    return `rgba(255, 236, 177, ${alpha})`;
  }

  function messageFont(channel, fontSize) {
    const style = channel === "whisper" ? "italic " : "";
    return `${style}600 ${fontSize}px Verdana, Geneva, sans-serif`;
  }

  function splitLongWord(word, maxWidth) {
    const chunks = [];
    let chunk = "";
    for (const char of word) {
      const candidate = chunk + char;
      if (ctx.measureText(candidate).width <= maxWidth || !chunk) {
        chunk = candidate;
        continue;
      }
      chunks.push(chunk);
      chunk = char;
    }
    if (chunk) chunks.push(chunk);
    return chunks;
  }

  function draw(now) {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    maybeAddDurgularYell(now);
    advanceSnake(now);
    drawSnake(now);
    drawBidens(now);
    drawCombatLog(now);
    requestAnimationFrame(draw);
  }

  resizeCanvas();
  resetSnake();
  window.addEventListener("resize", resizeCanvas);

  const events = new EventSource("/events");
  events.onmessage = (event) => {
    try {
      addSpawn(JSON.parse(event.data));
    } catch (_error) {
      // Ignore malformed overlay events.
    }
  };

  requestAnimationFrame(draw);
})();
