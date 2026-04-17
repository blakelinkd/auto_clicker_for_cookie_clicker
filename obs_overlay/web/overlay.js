(() => {
  "use strict";

  const canvas = document.getElementById("overlay");
  const ctx = canvas.getContext("2d");
  const config = Object.assign({ snakeEnabled: true }, window.OVERLAY_CONFIG || {});
  const assetVersion = "snake-heat-17";
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
  const snakeHeadDrawSize = 64;
  const snakeBodyDrawSize = 54;
  const cellSize = 68;
  const segmentCollisionGap = 4;
  const snakeTickMs = 230;
  const heatCandidateAngles = [0, 35, -35, 70, -70, 110, -110, 145, -145, 180];
  const enrageSpeedMultiplier = 1.82;
  const enrageSizeGrowthPerSecond = 1.12;
  const enrageVisualEaseMs = 3000;
  const enrageMeterMaxBidens = 15;
  const snake = {
    mode: "heat",
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
    enrageEatenCount: 0,
    enraged: false,
    enrageStart: 0,
    enrageEndedAt: 0,
    enrageDuration: 15000,
    enrageEatenThreshold: 15,
    heatTargeting: false,
    heatStuckSample: null,
    heatStuckSince: 0,
    heatRecoveryUntil: 0,
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
    snake.mode = "heat";
    snake.heatDirection = { x: 1, y: 0 };
    snake.direction = { x: 1, y: 0 };
    snake.grow = 0;
    snake.scanRow = Math.floor(gridHeight() / 2);
    snake.scanDirection = 1;
    snake.lastTick = performance.now();
    snake.lastFrame = snake.lastTick;
    snake.moveStartedAt = snake.lastTick;
    snake.heatStuckSample = null;
    snake.heatStuckSince = 0;
    snake.heatRecoveryUntil = 0;
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
      const clamped = clampHeatPointToViewport(segment);
      segment.x = clamped.x;
      segment.y = clamped.y;
    }
  }

  function clampHeatPointToViewport(point) {
    const margin = snakeHeadDrawSize / 2;
    return {
      x: Math.max(margin, Math.min(window.innerWidth - margin, point.x)),
      y: Math.max(margin, Math.min(window.innerHeight - margin, point.y)),
    };
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
      existingSpawn.hoverPhase = Math.random() * Math.PI * 2;
      existingSpawn.wigglePhase = Math.random() * Math.PI * 2;
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
      hoverPhase: Math.random() * Math.PI * 2,
      wigglePhase: Math.random() * Math.PI * 2,
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
    if (bidenSpawnCount % 5 === 0) {
      addCombatLogLine("grandma", "I'm going to open you up like a can of sardines!", now + 200);
    }
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

  function gridPointDistance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
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
    if (!isEnraged(now)) {
      snake.enrageEatenCount = Math.min(snake.enrageEatenThreshold, snake.enrageEatenCount + 1);
    }
    playSound(sounds.grandma);
    maybeStartEnrage(now);
  }

  function isEnraged(now) {
    return snake.enraged && now < snake.enrageStart + snake.enrageDuration;
  }

  function maybeStartEnrage(now) {
    if (isEnraged(now)) return;
    if (snake.enrageEatenCount < snake.enrageEatenThreshold) return;
    snake.enraged = true;
    snake.enrageStart = now;
    snake.enrageEndedAt = 0;
    snake.enrageEatenCount = snake.enrageEatenThreshold;
    addCombatLogLine("grandma", "ENRAGED!", now, "shout");
  }

  function updateEnrageState(now) {
    if (!snake.enraged) return;
    if (now < snake.enrageStart + snake.enrageDuration) return;
    snake.enraged = false;
    snake.enrageEndedAt = now;
    snake.enrageStart = 0;
    snake.enrageEatenCount = 0;
    addCombatLogLine("grandma", "Enrage spent.", now);
  }

  function enrageMovementMultiplier(now) {
    return isEnraged(now) ? enrageSpeedMultiplier : 1;
  }

  function effectiveSnakeTickMs(now) {
    return snakeTickMs / enrageMovementMultiplier(now);
  }

  function enrageSizeMultiplier(now) {
    const activeStart = snake.enrageStart > 0 ? snake.enrageStart : snake.enrageEndedAt - snake.enrageDuration;
    if (activeStart <= 0) return 1;
    const elapsedSeconds = Math.max(0, (Math.min(now, activeStart + snake.enrageDuration) - activeStart) / 1000);
    const peak = Math.pow(enrageSizeGrowthPerSecond, elapsedSeconds);
    if (isEnraged(now)) return peak;
    const ease = enrageVisualEaseFraction(now);
    return 1 + (peak - 1) * ease;
  }

  function enrageVisualEaseFraction(now) {
    if (isEnraged(now)) return 1;
    if (!snake.enrageEndedAt) return 0;
    const elapsed = Math.max(0, now - snake.enrageEndedAt);
    if (elapsed >= enrageVisualEaseMs) return 0;
    const t = elapsed / enrageVisualEaseMs;
    return (1 - Math.min(1, t)) ** 3;
  }

  function enrageVisualIntensity(now) {
    if (isEnraged(now)) return 1;
    return enrageVisualEaseFraction(now);
  }

  function enrageVisualPulseTime(now) {
    if (snake.enrageStart > 0) return now - snake.enrageStart;
    if (snake.enrageEndedAt > 0) return snake.enrageDuration + Math.max(0, now - snake.enrageEndedAt);
    return 0;
  }

  function enrageProgressFraction(now) {
    const threshold = enrageMeterThreshold();
    if (isEnraged(now)) return 1;
    return clamp01(snake.enrageEatenCount / threshold);
  }

  function enterHeatSeekingMode(now) {
    if (snake.mode === "heat" && snake.heatSegments.length > 0) return;
    snake.mode = "heat";
    snake.heatSegments = gridSegmentsToPixels(interpolatedSegments(now));
    if (snake.heatSegments.length === 0) {
      snake.heatSegments = gridSegmentsToPixels(snake.segments);
    }
    snake.heatDirection = { x: snake.direction.x, y: snake.direction.y };
    snake.lastFrame = now;
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
    updateEnrageState(now);
    enterHeatSeekingMode(now);
    advanceHeatSeeking(now);
  }

  function advanceGridSnake(now) {
    
    if (snake.segments.length === 0) resetSnake();
    if (!isInBounds(snake.segments[0])) {
      resetSnake();
    }
    if (now - snake.lastTick < effectiveSnakeTickMs(now)) return;
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
    if (target && !snake.heatTargeting) {
      addCombatLogLine("grandma", "Heat seeking mode engage!", now);
    }
    snake.heatTargeting = Boolean(target);
    const speed = (cellSize / snakeTickMs) * enrageMovementMultiplier(now);
    const maxStep = speed * dt;
    const sizes = segmentSizeMultipliers(snake.heatSegments.length);
    const targetPoint = target ? bidenCenter(target) : null;
    let desired = target
      ? vectorToward(head, bidenCenter(target))
      : snake.heatDirection;

    if (!target) {
      desired = bounceHeatDirection(head, desired);
    }
    desired = normalizeVector(addVectors(desired, wallEscapeVector(head, targetPoint)));
    if (snake.heatRecoveryUntil > now) {
      desired = normalizeVector(addVectors(desired, scaleVector(inwardWallVector(head), 4.5)));
    }
    desired = normalizeVector(addVectors(desired, heatTailAvoidanceVector(head, desired, maxStep, sizes)));

    const previousHead = { x: head.x, y: head.y };
    const chosenMove = chooseHeatMove(head, desired, maxStep, sizes, targetPoint);
    head.x = chosenMove.x;
    head.y = chosenMove.y;
    snake.heatDirection = chosenMove.direction;
    clampHeatSegmentsToViewport();
    if (heatHeadCollidesWithTail(head, sizes)) {
      const sidestep = chooseHeatSidestep(previousHead, desired, maxStep, sizes, targetPoint);
      head.x = sidestep.x;
      head.y = sidestep.y;
      snake.heatDirection = sidestep.direction;
      clampHeatSegmentsToViewport();
    }
    if (updateHeatStuckState(previousHead, head, now) || snake.heatRecoveryUntil > now) {
      applyHeatStuckRecovery(head, sizes, maxStep, now);
    }

    if (target && pixelDistance(head, bidenCenter(target)) <= cellSize * 0.55) {
      const tail = snake.heatSegments[snake.heatSegments.length - 1] || head;
      snake.heatSegments.push({ x: tail.x, y: tail.y });
      handleBidenEaten(target, now);
    }

    relaxHeatTail();
  }

  function updateHeatStuckState(previousHead, head, now) {
    if (heatWallContactCount(head) === 0) {
      snake.heatStuckSample = null;
      snake.heatStuckSince = 0;
      return false;
    }

    const movedThisFrame = pixelDistance(previousHead, head);
    if (movedThisFrame > cellSize * 0.18) {
      snake.heatStuckSample = { x: head.x, y: head.y, at: now };
      snake.heatStuckSince = 0;
      return false;
    }

    if (!snake.heatStuckSample || pixelDistance(snake.heatStuckSample, head) > cellSize * 0.45) {
      snake.heatStuckSample = { x: head.x, y: head.y, at: now };
      snake.heatStuckSince = 0;
      return false;
    }

    const pinnedMs = now - snake.heatStuckSample.at;
    if (pinnedMs < 650) return false;
    if (!snake.heatStuckSince) snake.heatStuckSince = now;
    snake.heatRecoveryUntil = Math.max(snake.heatRecoveryUntil, now + 900);
    snake.heatStuckSample = { x: head.x, y: head.y, at: now };
    return true;
  }

  function applyHeatStuckRecovery(head, sizes, maxStep, now) {
    const inward = inwardWallVector(head);
    if (Math.abs(inward.x) <= 0.001 && Math.abs(inward.y) <= 0.001) return;

    const recoveryProgress = Math.max(0, Math.min(1, (snake.heatRecoveryUntil - now) / 900));
    const headStep = Math.max(maxStep, cellSize * (0.28 + recoveryProgress * 0.16));
    const recoveredHead = clampHeatPointToViewport({
      x: head.x + inward.x * headStep,
      y: head.y + inward.y * headStep,
    });
    head.x = recoveredHead.x;
    head.y = recoveredHead.y;
    snake.heatDirection = inward;

    for (let i = 1; i < snake.heatSegments.length; i += 1) {
      const segment = snake.heatSegments[i];
      const awayFromHead = vectorAwayFrom(head, segment, inward);
      const falloff = Math.max(0.2, 1 - (i / Math.max(2, snake.heatSegments.length)));
      const push = cellSize * 0.42 * falloff;
      const moved = clampHeatPointToViewport({
        x: segment.x + inward.x * push + awayFromHead.x * push * 0.85,
        y: segment.y + inward.y * push + awayFromHead.y * push * 0.85,
      });
      segment.x = moved.x;
      segment.y = moved.y;
    }
    enforceSegmentCollisionGaps(snake.heatSegments, sizes, 1);
    clampHeatSegmentsToViewport();
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

  function addVectors(a, b) {
    return {
      x: a.x + b.x,
      y: a.y + b.y,
    };
  }

  function scaleVector(vector, scale) {
    return {
      x: vector.x * scale,
      y: vector.y * scale,
    };
  }

  function normalizeVector(vector) {
    const length = Math.sqrt(vector.x * vector.x + vector.y * vector.y);
    if (length <= 0.001) {
      return { x: 1, y: 0 };
    }
    return {
      x: vector.x / length,
      y: vector.y / length,
    };
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

  function wallEscapeVector(head, targetPoint) {
    const margin = snakeHeadDrawSize / 2;
    const influence = Math.max(cellSize * 1.65, 1);
    const left = Math.max(0, influence - (head.x - margin));
    const right = Math.max(0, influence - ((window.innerWidth - margin) - head.x));
    const top = Math.max(0, influence - (head.y - margin));
    const bottom = Math.max(0, influence - ((window.innerHeight - margin) - head.y));
    const horizontalPressure = Math.max(left, right) / influence;
    const verticalPressure = Math.max(top, bottom) / influence;
    const cornerPressure = horizontalPressure * verticalPressure;
    const targetPullsIntoWall = targetPoint
      && ((left > 0 && targetPoint.x < head.x)
        || (right > 0 && targetPoint.x > head.x)
        || (top > 0 && targetPoint.y < head.y)
        || (bottom > 0 && targetPoint.y > head.y));
    const strength = 1.2 + cornerPressure * 3.8 + (targetPullsIntoWall ? 1.4 : 0);
    return {
      x: ((left - right) / influence) * strength,
      y: ((top - bottom) / influence) * strength,
    };
  }

  function inwardWallVector(point) {
    const margin = snakeHeadDrawSize / 2;
    const influence = Math.max(cellSize * 1.25, 1);
    const left = Math.max(0, influence - (point.x - margin));
    const right = Math.max(0, influence - ((window.innerWidth - margin) - point.x));
    const top = Math.max(0, influence - (point.y - margin));
    const bottom = Math.max(0, influence - ((window.innerHeight - margin) - point.y));
    const vector = {
      x: left > right ? 1 : right > left ? -1 : 0,
      y: top > bottom ? 1 : bottom > top ? -1 : 0,
    };
    if (Math.abs(vector.x) <= 0.001 && Math.abs(vector.y) <= 0.001) {
      return { x: 0, y: 0 };
    }
    return normalizeVector(vector);
  }

  function heatWallContactCount(point) {
    const margin = snakeHeadDrawSize / 2;
    const contact = Math.max(6, cellSize * 0.12);
    let contacts = 0;
    if (point.x - margin <= contact) contacts += 1;
    if (window.innerWidth - margin - point.x <= contact) contacts += 1;
    if (point.y - margin <= contact) contacts += 1;
    if (window.innerHeight - margin - point.y <= contact) contacts += 1;
    return contacts;
  }

  function outwardWallPressure(point, direction) {
    const margin = snakeHeadDrawSize / 2;
    const influence = Math.max(cellSize * 1.25, 1);
    let pressure = 0;
    if (point.x - margin < influence && direction.x < 0) {
      pressure += ((influence - (point.x - margin)) / influence) * Math.abs(direction.x);
    }
    if (window.innerWidth - margin - point.x < influence && direction.x > 0) {
      pressure += ((influence - (window.innerWidth - margin - point.x)) / influence) * direction.x;
    }
    if (point.y - margin < influence && direction.y < 0) {
      pressure += ((influence - (point.y - margin)) / influence) * Math.abs(direction.y);
    }
    if (window.innerHeight - margin - point.y < influence && direction.y > 0) {
      pressure += ((influence - (window.innerHeight - margin - point.y)) / influence) * direction.y;
    }
    return pressure;
  }

  function heatTailAvoidanceVector(head, desired, maxStep, sizes) {
    const predicted = {
      x: head.x + desired.x * maxStep,
      y: head.y + desired.y * maxStep,
    };
    const headRadius = segmentCollisionRadius(0, sizes);
    const avoidanceRange = headRadius + snakeBodyDrawSize * 0.85;
    let avoid = { x: 0, y: 0 };

    for (let i = 2; i < snake.heatSegments.length; i += 1) {
      const segment = snake.heatSegments[i];
      const requiredDistance = segmentCollisionSpacing(0, i, sizes);
      const dx = predicted.x - segment.x;
      const dy = predicted.y - segment.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const influence = Math.max(requiredDistance + avoidanceRange, 1);
      if (distance >= influence) continue;

      const strength = (influence - distance) / influence;
      const pushX = distance > 0.001 ? dx / distance : -desired.y;
      const pushY = distance > 0.001 ? dy / distance : desired.x;
      avoid.x += pushX * strength * 2.2;
      avoid.y += pushY * strength * 2.2;
    }
    return avoid;
  }

  function heatHeadCollidesWithTail(head, sizes) {
    for (let i = 2; i < snake.heatSegments.length; i += 1) {
      if (pixelDistance(head, snake.heatSegments[i]) < segmentCollisionSpacing(0, i, sizes)) {
        return true;
      }
    }
    return false;
  }

  function chooseHeatSidestep(previousHead, desired, maxStep, sizes, targetPoint) {
    return chooseHeatMove(previousHead, desired, maxStep, sizes, targetPoint);
  }

  function chooseHeatMove(origin, desired, maxStep, sizes, targetPoint) {
    if (maxStep <= 0.001) {
      return { x: origin.x, y: origin.y, direction: normalizeVector(desired) };
    }

    const baseDirection = normalizeVector(desired);
    let best = null;
    for (const direction of heatCandidateDirections(origin, baseDirection)) {
      const point = clampHeatPointToViewport({
        x: origin.x + direction.x * maxStep,
        y: origin.y + direction.y * maxStep,
      });
      const actualDirection = actualHeatMoveDirection(origin, point, direction);
      const score = scoreHeatMove(origin, point, actualDirection, baseDirection, sizes, targetPoint);
      const candidate = { x: point.x, y: point.y, direction: actualDirection, score };
      if (!best || candidate.score > best.score) {
        best = candidate;
      }
    }

    return best || { x: origin.x, y: origin.y, direction: baseDirection };
  }

  function heatCandidateDirections(origin, baseDirection) {
    const directions = [];
    const escapeDirection = inwardWallVector(origin);
    if (Math.abs(escapeDirection.x) > 0.001 || Math.abs(escapeDirection.y) > 0.001) {
      directions.push(escapeDirection);
    }
    for (const degrees of heatCandidateAngles) {
      const radians = degrees * Math.PI / 180;
      const cos = Math.cos(radians);
      const sin = Math.sin(radians);
      directions.push(normalizeVector({
        x: baseDirection.x * cos - baseDirection.y * sin,
        y: baseDirection.x * sin + baseDirection.y * cos,
      }));
    }
    return directions;
  }

  function actualHeatMoveDirection(origin, point, fallbackDirection) {
    const dx = point.x - origin.x;
    const dy = point.y - origin.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > 0.001) {
      return { x: dx / distance, y: dy / distance };
    }
    const inward = inwardWallVector(origin);
    const combined = addVectors(inward, fallbackDirection);
    const combinedLength = Math.sqrt(combined.x * combined.x + combined.y * combined.y);
    if (combinedLength > 0.001) {
      return { x: combined.x / combinedLength, y: combined.y / combinedLength };
    }
    return Math.abs(inward.x) > 0.001 || Math.abs(inward.y) > 0.001 ? inward : normalizeVector(fallbackDirection);
  }

  function vectorAwayFrom(origin, point, fallbackDirection) {
    const dx = point.x - origin.x;
    const dy = point.y - origin.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > 0.001) {
      return { x: dx / distance, y: dy / distance };
    }
    return fallbackDirection;
  }

  function scoreHeatMove(origin, point, direction, baseDirection, sizes, targetPoint) {
    const clearance = heatTailClearance(point, sizes);
    const requiredClearance = minHeatTailSpacing(sizes);
    const collisionPenalty = clearance < requiredClearance ? (requiredClearance - clearance) * 80 : 0;
    const wallMargin = heatWallMargin(point);
    const turnPenalty = (1 - Math.max(-1, Math.min(1, direction.x * baseDirection.x + direction.y * baseDirection.y))) * 14;
    const movement = pixelDistance(origin, point);
    const targetGain = targetPoint
      ? pixelDistance(origin, targetPoint) - pixelDistance(point, targetPoint)
      : 0;
    const wallPenalty = wallEscapeMagnitude(point) * 22;
    const outwardPenalty = outwardWallPressure(origin, direction) * 120;

    return clearance * 4 + wallMargin * 0.25 + movement * 2 + targetGain * 3 - turnPenalty - collisionPenalty - wallPenalty - outwardPenalty;
  }

  function wallEscapeMagnitude(point) {
    const escape = wallEscapeVector(point, null);
    return Math.sqrt(escape.x * escape.x + escape.y * escape.y);
  }

  function heatTailClearance(point, sizes) {
    let clearance = Infinity;
    for (let i = 2; i < snake.heatSegments.length; i += 1) {
      const distance = pixelDistance(point, snake.heatSegments[i]) - segmentCollisionSpacing(0, i, sizes);
      clearance = Math.min(clearance, distance);
    }
    return Number.isFinite(clearance) ? clearance : minHeatTailSpacing(sizes);
  }

  function minHeatTailSpacing(sizes) {
    if (sizes.length < 3) return 0;
    let spacing = Infinity;
    for (let i = 2; i < sizes.length; i += 1) {
      spacing = Math.min(spacing, segmentCollisionSpacing(0, i, sizes));
    }
    return Number.isFinite(spacing) ? spacing : 0;
  }

  function heatWallMargin(point) {
    const margin = snakeHeadDrawSize / 2;
    return Math.min(
      point.x - margin,
      window.innerWidth - margin - point.x,
      point.y - margin,
      window.innerHeight - margin - point.y
    );
  }

  function relaxHeatTail() {
    const sizes = segmentSizeMultipliers(snake.heatSegments.length);
    for (let i = 1; i < snake.heatSegments.length; i += 1) {
      const leader = snake.heatSegments[i - 1];
      const follower = snake.heatSegments[i];
      const spacing = segmentCollisionSpacing(i - 1, i, sizes);
      const dx = follower.x - leader.x;
      const dy = follower.y - leader.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance > spacing && distance > 0.001) {
        follower.x = leader.x + (dx / distance) * spacing;
        follower.y = leader.y + (dy / distance) * spacing;
      }
    }
    enforceSegmentCollisionGaps(snake.heatSegments, sizes, 1);
  }

  function interpolatedSegments(now) {
    const elapsed = Math.max(0, now - snake.moveStartedAt);
    const t = Math.min(1, elapsed / effectiveSnakeTickMs(now));
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

  function compactVisualSegments(segments, sizes) {
    if (segments.length < 2) return segments;
    const compacted = [segments[0]];
    let pathIndex = 0;
    let pathStart = segments[0];
    let pathEnd = segments[1];
    let pathRemaining = gridPointDistance(pathStart, pathEnd);

    for (let i = 1; i < segments.length; i += 1) {
      let targetDistance = segmentCollisionSpacing(i - 1, i, sizes) / cellSize;
      while (targetDistance > pathRemaining && pathIndex < segments.length - 2) {
        targetDistance -= pathRemaining;
        pathIndex += 1;
        pathStart = segments[pathIndex];
        pathEnd = segments[pathIndex + 1];
        pathRemaining = gridPointDistance(pathStart, pathEnd);
      }

      if (pathRemaining <= 0.001) {
        compacted.push({ x: pathStart.x, y: pathStart.y });
        continue;
      }

      const t = Math.min(1, targetDistance / pathRemaining);
      compacted.push({
        x: pathStart.x + (pathEnd.x - pathStart.x) * t,
        y: pathStart.y + (pathEnd.y - pathStart.y) * t,
      });
      pathRemaining -= targetDistance;
      pathStart = compacted[compacted.length - 1];
    }
    return compacted;
  }

  function drawSnake(now) {
    if (!config.snakeEnabled) return;
    if (!grandmaHeadSprite.complete || !grandmaHeadSprite.naturalWidth || !grandmaHeadSprite.naturalHeight) return;
    if (snake.mode === "heat") {
      drawHeatSeekingSnake(now);
      return;
    }
    
      const width = gridWidth();
      const height = gridHeight();
      const offsetX = (window.innerWidth - width * cellSize) / 2;
      const offsetY = (window.innerHeight - height * cellSize) / 2;
      const sizes = segmentSizeMultipliers(snake.segments.length);
      const visualSegments = compactVisualSegments(interpolatedSegments(now), sizes);
      enforceSegmentCollisionGaps(visualSegments, sizes, cellSize);
      
      // Draw segments from tail to head (so head draws on top)
      for (let i = visualSegments.length - 1; i >= 0; i -= 1) {
        const segment = visualSegments[i];
        const isHead = i === 0;
        
        // Base grid position
        const x = offsetX + segment.x * cellSize;
        const y = offsetY + segment.y * cellSize;
        
        const baseSize = isHead ? snakeHeadDrawSize : snakeBodyDrawSize;
        const size = baseSize * sizes[i] * enrageSizeMultiplier(now);
        const bob = isHead ? Math.sin(performance.now() / 140) * 2 : 0;

        ctx.save();
        ctx.translate(x + cellSize / 2, y + cellSize / 2 + bob);
        drawGrandmaHead(now, size);
        ctx.restore();
      }
  }

  function drawHeatSeekingSnake(now) {
    const sizes = segmentSizeMultipliers(snake.heatSegments.length);
    for (let i = snake.heatSegments.length - 1; i >= 0; i -= 1) {
      const segment = snake.heatSegments[i];
      const isHead = i === 0;
      const baseSize = isHead ? snakeHeadDrawSize : snakeBodyDrawSize;
      const size = baseSize * sizes[i] * enrageSizeMultiplier(now);
      const bob = isHead ? Math.sin(now / 140) * 2 : 0;

      ctx.save();
      ctx.translate(segment.x, segment.y + bob);
      drawGrandmaHead(now, size);
      ctx.restore();
    }
  }

  function drawGrandmaHead(now, size) {
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(grandmaHeadSprite, -size / 2, -size / 2, size, size);
    const intensity = enrageVisualIntensity(now);
    if (intensity <= 0) return;

    const pulse = (Math.sin(enrageVisualPulseTime(now) / 95) + 1) / 2;
    ctx.globalCompositeOperation = "source-atop";
    ctx.globalAlpha = (0.34 + pulse * 0.34) * intensity;
    ctx.fillStyle = pulse > 0.5 ? "rgb(255, 24, 24)" : "rgb(255, 96, 0)";
    ctx.fillRect(-size / 2, -size / 2, size, size);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function segmentSizeMultipliers(count) {
    const sizes = [];
    let multiplier = 1;
    const shrinkFactor = 0.96;
    const minThreshold = 0.62;

    for (let i = 0; i < count; i += 1) {
      sizes.push(multiplier);
      multiplier = Math.max(minThreshold, multiplier * shrinkFactor);
    }
    return sizes;
  }

  function segmentCollisionRadius(index, sizes) {
    const baseSize = index === 0 ? snakeHeadDrawSize : snakeBodyDrawSize;
    return (baseSize * sizes[index]) / 2;
  }

  function segmentCollisionSpacing(firstIndex, secondIndex, sizes) {
    const collisionSpacing = segmentCollisionRadius(firstIndex, sizes)
      + segmentCollisionRadius(secondIndex, sizes)
      + segmentCollisionGap;
    return collisionSpacing;
  }

  function enforceSegmentCollisionGaps(segments, sizes, coordinateScale) {
    for (let i = 1; i < segments.length; i += 1) {
      for (let j = 0; j < i; j += 1) {
        const requiredDistance = segmentCollisionSpacing(j, i, sizes) / coordinateScale;
        const dx = segments[i].x - segments[j].x;
        const dy = segments[i].y - segments[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance >= requiredDistance) continue;

        const pushX = distance > 0.001 ? dx / distance : 1;
        const pushY = distance > 0.001 ? dy / distance : 0;
        segments[i].x = segments[j].x + pushX * requiredDistance;
        segments[i].y = segments[j].y + pushY * requiredDistance;
      }
    }
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
        drawBidenSprite(spawn, scale, opacity, now, proximityFactor, eatProgress);
        continue;
      }
      
      // Normal biden - proximity-based shrink and wiggle
      if (!bidenSprite.complete || !bidenSprite.naturalWidth || !bidenSprite.naturalHeight) continue;
      
      // Keep targets readable while Grandma approaches; eating handles the vanish.
      const shrinkFactor = Math.pow(proximityFactor, 2.2) * 0.22;
      const scale = 1 - shrinkFactor;
      const opacity = 1;
      
      drawBidenSprite(spawn, scale, opacity, now, proximityFactor);
    }
  }

  function drawBidenSprite(spawn, scale, opacity, now, proximityFactor, eatenProgress = 0) {
    const baseHeight = defaultBidenHeight;
    const baseWidth = bidenSprite.naturalWidth * (baseHeight / bidenSprite.naturalHeight);
    const drawWidth = baseWidth * scale;
    const drawHeight = baseHeight * scale;
    let targetX = spawn.normX * window.innerWidth;
    let targetY = spawn.normY * window.innerHeight;
    
    const age = Math.max(0, now - (spawn.startedAt || now));
    const subtleEase = Math.min(1, age / 650);
    const hoverPhase = Number.isFinite(spawn.hoverPhase) ? spawn.hoverPhase : 0;
    const wigglePhase = Number.isFinite(spawn.wigglePhase) ? spawn.wigglePhase : 0;
    const subtleWiggle = Math.sin((now / 380) + wigglePhase) * 3.2 * subtleEase;
    const hover = Math.sin((now / 520) + hoverPhase) * 5.0 * subtleEase;

    // Frantic wiggle based on proximity
    const wiggleIntensity = proximityFactor * 15;
    const wiggleSpeed = 50 + (proximityFactor * 100); // faster when closer
    const wiggle = Math.sin(now / wiggleSpeed) * wiggleIntensity;
    targetX += subtleWiggle + wiggle;
    targetY += hover;
    
    const drawX = targetX - (drawWidth * fingerAnchor.x);
    const drawY = targetY - (drawHeight * fingerAnchor.y);

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(bidenSprite, drawX, drawY, drawWidth, drawHeight);
    drawBidenEatenFlash(now, drawX, drawY, drawWidth, drawHeight, eatenProgress);
    ctx.restore();
  }

  function drawBidenEatenFlash(now, drawX, drawY, drawWidth, drawHeight, eatenProgress) {
    if (eatenProgress <= 0) return;
    const pulse = (Math.sin(now / 55) + 1) / 2;
    const intensity = (1 - eatenProgress * 0.35) * (0.42 + pulse * 0.42);
    ctx.globalCompositeOperation = "source-atop";
    ctx.globalAlpha *= intensity;
    ctx.fillStyle = pulse > 0.5 ? "rgb(255, 24, 24)" : "rgb(255, 96, 0)";
    ctx.fillRect(drawX, drawY, drawWidth, drawHeight);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
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

  function enrageMeterThreshold() {
    const threshold = Number(snake.enrageEatenThreshold);
    return Number.isFinite(threshold) && threshold > 0 ? threshold : enrageMeterMaxBidens;
  }

  function enrageMeterIsEnraged(now) {
    if (typeof isEnraged === "function") {
      return isEnraged(now);
    }
    if (Number.isFinite(snake.enragedUntil)) {
      return now < snake.enragedUntil;
    }
    if (Number.isFinite(snake.enrageStart) && snake.enrageStart > 0
      && Number.isFinite(snake.enrageDuration) && snake.enrageDuration > 0) {
      return now < snake.enrageStart + snake.enrageDuration;
    }
    return Boolean(snake.enraged);
  }

  function enrageMeterEatenCount(now) {
    const threshold = enrageMeterThreshold();
    if (enrageMeterIsEnraged(now)) return threshold;
    const enrageCount = Number(snake.enrageEatenCount);
    if (Number.isFinite(enrageCount)) return Math.max(0, Math.min(threshold, enrageCount));
    const eatenCount = Number(snake.eatenCount);
    if (!Number.isFinite(eatenCount)) return 0;
    return Math.max(0, Math.min(threshold, eatenCount % threshold));
  }

  function enrageMeterProgressFraction(now) {
    if (typeof enrageProgressFraction === "function") {
      return clamp01(enrageProgressFraction(now));
    }
    return clamp01(enrageMeterEatenCount(now) / enrageMeterThreshold());
  }

  function drawEnrageMeter(now) {
    if (!config.snakeEnabled) return;

    const threshold = enrageMeterThreshold();
    const eatenCount = enrageMeterEatenCount(now);
    const progress = enrageMeterProgressFraction(now);
    const width = Math.min(460, Math.max(280, window.innerWidth * 0.32));
    const height = 82;
    const x = (window.innerWidth - width) / 2;
    const y = Math.max(12, window.innerHeight * 0.05);
    const padding = 10;
    const barHeight = 17;
    const barX = x + padding;
    const barY = y + height - padding - barHeight;
    const barWidth = width - padding * 2;
    const red = "rgba(235, 35, 35, 0.94)";

    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.82)";
    ctx.strokeStyle = red;
    ctx.lineWidth = 2;
    ctx.fillRect(x, y, width, height);
    ctx.strokeRect(x + 1, y + 1, width - 2, height - 2);

    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.shadowColor = "rgba(0, 0, 0, 0.95)";
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = red;
    ctx.font = "700 17px Verdana, Geneva, sans-serif";
    ctx.fillText("GRAKE ENRAGE METER", x + width / 2, y + 9, width - padding * 2);

    ctx.font = "700 14px Verdana, Geneva, sans-serif";
    ctx.fillText(`${Math.round(eatenCount)} / ${threshold} BIDENS`, x + width / 2, y + 36, width - padding * 2);

    ctx.shadowColor = "transparent";
    ctx.fillStyle = "rgba(0, 0, 0, 0.95)";
    ctx.strokeStyle = red;
    ctx.lineWidth = 1;
    ctx.fillRect(barX, barY, barWidth, barHeight);
    ctx.strokeRect(barX + 0.5, barY + 0.5, barWidth - 1, barHeight - 1);
    ctx.fillStyle = red;
    ctx.fillRect(barX + 2, barY + 2, Math.max(0, (barWidth - 4) * progress), barHeight - 4);
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
    drawEnrageMeter(now);
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
