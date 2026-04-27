(() => {
  "use strict";

  const canvas = document.getElementById("overlay");
  const ctx = canvas.getContext("2d");
  const config = Object.assign({ snakeEnabled: true, logOnly: false }, window.OVERLAY_CONFIG || {});
  const assetVersion = "snake-heat-worm-45";
  const bidenSprite = new Image();
  const grandmaHeadSprite = new Image();
  const fakeCursorSprite = new Image();
  const poopSprite = new Image();
  const sounds = {
    dean: createAudioPool(`/assets/audio/dean_scream.mp3?v=${assetVersion}`, 0.65, 3),
    grandma: createAudioPool(`/assets/audio/grandma_cookie.mp3?v=${assetVersion}`, 0.45, 4),
    poop: createAudioPool(`/assets/audio/farting_sound.mp3?v=${assetVersion}`, 0.55, 8),
    chomp: createAudioPool(`/assets/audio/chomp_sound_effect.mp3?v=${assetVersion}`, 0.48, 6),
    flyZap: createAudioPool(`/assets/audio/fly_zap.mp3?v=${assetVersion}`, 0.5, 10),
    // Disabled until fly_buzz.mp3 is replaced; the current file is the same scream as grandma_cookie.mp3.
    fly: null,
  };
   let flySoundActive = false;
   let animationFrameId = null;
   let events = null;
   const bidenSpawns = [];
   const bidenSpawnByShimmerId = new Map();

  const fingerAnchor = { x: 0.0071, y: 0.1389 };
  const defaultBidenHeight = 320;
  const snakeHeadDrawSize = 64;
  const snakeBodyDrawSize = 54;
  const cellSize = 68;
  const segmentCollisionGap = 0;
  const heatSegmentVisualGap = 2;
  const snakeTickMs = 230;
  const heatCandidateAngles = [0, 35, -35, 70, -70, 110, -110, 145, -145, 180];
  const enrageSpeedMultiplier = 1.82;
  const enrageSizeGrowthPerSecond = 1.12;
  const enrageVisualEaseMs = 3000;
  const enrageMeterMaxBidens = 15;
  const babyGrandmaDrawScale = 0.62;
  const babyGrandmaSpeedMultiplier = 0.84;
  const superGrandmaPoopChance = 0.3;
  const superGrandmaDrawScale = 1.28;
  const superGrandmaSpeedMultiplier = 1.2;
  const grandmaMaxHp = 150;
  const grandmaMaxCount = 30; // maximum total grandmas (including main snake)
  const flyMaxCount = 60; // maximum total flies
  const bidenEatRadius = cellSize * 1.08;
  const bidenCloseRange = cellSize * 3.2;
  const bidenWaypointLimit = 10;
  const fakeCursorDrawSize = 64;
  const fakeCursorSpeed = 92 * 3;
  const fakeCursorMinPauseMs = 1000;
  const fakeCursorMaxPauseMs = 5000;
  const fakeCursorMinPathMs = 2600;
  const fakeCursorMaxPathMs = 7200;
  const poopFrameCount = 6;
  const poopDropIntervalMs = 20000;
  const grandmaSpawnSpacingMs = 1500;
  const poopAnimationFrameMs = 120;
  const poopGrowDurationMs = 850;
  const poopStartScale = 0.2;
  const poopDrawSize = 92;
  const poopGravity = 780;
  const poopTailImpulse = 120;
  const poopRestitution = 0.12;
  const poopFriction = 0.82;
  const poopAirDrag = 0.996;
  const poopAngularDrag = 0.985;
  const poopPhysicsSubstepMs = 16;
  const poopFloorFootprintScale = 0.72;
  const poopSleepLinearSpeed = 10;
  const poopSleepAngularSpeed = 0.16;
  const poopSleepDelayMs = 650;
  const wormSpawnEveryPoops = 1;
  const wormBaseScale = 1.08;
  const wormCrawlSpeed = 100;
  const wormInchwormArch = 7;
  const wormInchwormContract = 0.12;
  const wormGroundMargin = 3;
  const wormGroundReach = 28;
  const wormPatrolMargin = 28;
  const wormEatDurationMs = 2000;
  const wormCrunchIntervalMs = 520;
  const wormHeadShakeSize = 3.5;
  const wormGrowthMultiplier = 1.12;
  const wormMaxScale = 1.42;
  const wormPoopsToFly = 10;
  const wormRigScale = wormBaseScale;
  const wormDissolveDurationMs = 5000;
  const poopTimeToLiveMs = 2 * 60 * 1000; // 2 minutes
  const poopDissolveDurationMs = wormDissolveDurationMs;
  const superSnakeSpawnTimeoutMs = 3 * 60 * 1000; // 3 minutes
  const wormPoopClaimTimeoutMs = 2500;
  const wormMaxTargetHorizontalSpeed = 20;
  const wormDirectionChangeCooldownMs = 200;
  const wormDirectionDeadZone = 10;
  const flySpriteScale = 1.08;
  const flyStartScale = 0.125;
  const flyGrowDurationMs = 300000;
  const flyMinPauseMs = 1500;
  const flyMaxPauseMs = 4000;
  const flyMinFlightMs = 2000;
  const flyMaxFlightMs = 5000;
  const flySpeed = 180;
  const flyPatrolMargin = 40;
  const flyLifetimeMs = 24 * 60 * 60 * 1000;
  const flyCorpseDeleteMs = 3 * 60 * 1000;
  const flyZapDamage = 20;
  const flyZapRange = 620;
  const flyZapDurationMs = 130;
  const flyZapMinCooldownMs = 1275;
  const flyZapMaxCooldownMs = 2475;
  const flyZapColors = [
    { beam: "rgba(255, 38, 38, 0.9)", core: "rgba(255, 220, 220, 0.95)", ball: "rgba(255, 96, 96, 0.95)" },
    { beam: "rgba(42, 144, 255, 0.9)", core: "rgba(210, 236, 255, 0.95)", ball: "rgba(98, 188, 255, 0.95)" },
    { beam: "rgba(255, 126, 30, 0.9)", core: "rgba(255, 230, 190, 0.95)", ball: "rgba(255, 170, 74, 0.95)" },
    { beam: "rgba(255, 226, 34, 0.9)", core: "rgba(255, 252, 190, 0.95)", ball: "rgba(255, 244, 94, 0.95)" },
  ];
  const twitchChatQuipIntervalMs = 180000;
  const gmGithubQuip = "Want to try the auto-clicker? github.com/blakelinkd/auto_clicker_for_cookie_clicker";
  const gmGithubQuipIntervalMs = 300000;
  const defaultHudMessageTtlMs = 4000;
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
    maxHp: grandmaMaxHp,
    hp: grandmaMaxHp,
    dead: false,
    heatTargeting: false,
    heatStuckSample: null,
    heatStuckSince: 0,
    heatRecoveryUntil: 0,
  };
  const babyGrandmaSnakes = [];
  const grandmaPoops = [];
  const poopWorms = [];
  const bidenWaypointBuffer = [];
  const fakeCursor = {
    x: 0,
    y: 0,
    initialized: false,
    path: null,
    waitUntil: 0,
  };
  const combatLog = [];
  const hudMessages = [];
  const bidenTimer = {
    available: false,
    remainingSeconds: null,
    receivedAt: 0,
    onScreen: 0,
    resetAt: 0,
  };
  let lastDurgularYell = 0;
  let lastTwitchChatQuip = 0;
  let lastGmGithubQuip = 0;
  let lastGrandmaPoopAt = 0;
  let lastGrandmaSpawnTime = 0; // timestamp of last grandma spawn (any type) for spacing
  let totalGrandmaPoopsSpawned = 0;
  let pendingPoopWormSpawns = 0;
  let pendingWormBecomingSuperGrandma = false;
  let lastHungrySuperGrandmaSpawn = 0;
  let lastGrandmaSnakeGoneAt = 0;
  let bidenSpawnCount = 0;
  let nextPoopWormId = 1;
  let wormSprite = null;
  let flySprite = null;
  let flyManifest = null;
  const flies = [];
  const flyZaps = [];
  const biotachyonicWhisper = "it's supposed to look like biden is popping the cookies...";
  const twitchChatQuip = "Feel free to point out any bugs, make suggestions or request in the twitch chat!";
  const bidenFocusLines = [
    "Oh, it's focused.",
    "I'd say it's... I think it's...",
    "I have trouble even mentioning the number of years.",
    "I don't think of myself that way.",
    "I haven't noticed things I can't do.",
    "Physical, mental, anything else.",
  ];
  /*
   * Current WoW class colors from RAID_CLASS_COLORS / C_ClassColor.GetClassColor():
   * Death Knight #C41E3A, Demon Hunter #A330C9, Druid #FF7C0A,
   * Evoker #33937F, Hunter #AAD372, Mage #3FC7EB, Monk #00FF98,
   * Paladin #F48CBA, Priest #FFFFFF, Rogue #FFF468, Shaman #0070DD,
   * Warlock #8788EE, Warrior #C69B6D.
   */
  const wowClassColors = {
    biden: [170, 211, 114],
    durgular: [198, 155, 109],
    grandma: [135, 136, 238],
    biotachyonic: [255, 124, 10],
    fakecursor: [63, 199, 235],
    gm: [255, 200, 30],
  };
  const durgularLines = [
    "DURGULAAAAAR!",
    "DURGULAR!!",
    "DURGULAAAAAAAAAR!!!",
    "DUR-GU-LAR!",
    "DURGULAAAAAR!!!!",
  ];

  bidenSprite.src = "/assets/biden_i_did_that.png";
  grandmaHeadSprite.src = `/assets/game/grandma_head_smooth.png?v=${assetVersion}`;
  fakeCursorSprite.src = `/assets/game/cursor.png?v=${assetVersion}`;
  poopSprite.src = `/assets/sprites/poop.png?v=${assetVersion}`;

  function createAudioPool(src, volume, count, loop = false) {
    const clips = [];
    for (let i = 0; i < count; i += 1) {
      const audio = new Audio(src);
      audio.preload = "auto";
      audio.volume = volume;
      audio.muted = false;
      audio.setAttribute("playsinline", "");
      audio.loop = loop;
      audio.style.display = "none";
      document.body.appendChild(audio);
      audio.load();
      clips.push(audio);
    }
    return { clips, next: 0 };
  }

  function playSound(pool, loop = false) {
    if (!pool || pool.clips.length === 0) return;
    const audio = pool.clips[pool.next];
    pool.next = (pool.next + 1) % pool.clips.length;
    try {
      audio.pause();
      audio.currentTime = 0;
      audio.loop = loop;
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

  function stopSound(pool) {
    if (!pool || !pool.clips) return;
    for (const clip of pool.clips) {
      clip.pause();
      clip.currentTime = 0;
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
      clampHeatSegmentsToViewport(snake);
      for (const baby of babyGrandmaSnakes) {
        clampHeatSegmentsToViewport(baby);
      }
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
    snake.maxHp = grandmaMaxHp;
    snake.hp = grandmaMaxHp;
    snake.dead = false;
    babyGrandmaSnakes.length = 0;
    lastGrandmaPoopAt = snake.lastTick;
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

  function clampHeatSegmentsToViewport(heatSnake = snake) {
    const margin = snakeHeadDrawSize / 2;
    for (const segment of heatSnake.heatSegments) {
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
      rememberBidenWaypoint(normX, normY);
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
    rememberBidenWaypoint(normX, normY);
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

  function rememberBidenWaypoint(normX, normY) {
    bidenWaypointBuffer.push({ normX, normY });
    while (bidenWaypointBuffer.length > bidenWaypointLimit) {
      bidenWaypointBuffer.shift();
    }
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

  function maybeAddTwitchChatQuip(now) {
    if (lastTwitchChatQuip === 0) {
      lastTwitchChatQuip = now;
      return;
    }
    if (now - lastTwitchChatQuip < twitchChatQuipIntervalMs) return;
    addCombatLogLine("biotachyonic", twitchChatQuip, now, "whisper");
    lastTwitchChatQuip = now;
  }

  function maybeAddGmGithubQuip(now) {
    if (lastGmGithubQuip === 0) {
      lastGmGithubQuip = now;
      addCombatLogLine("gm", gmGithubQuip, now, "say");
      return;
    }
    if (now - lastGmGithubQuip < gmGithubQuipIntervalMs) return;
    addCombatLogLine("gm", gmGithubQuip, now, "say");
    lastGmGithubQuip = now;
  }

  function refreshBidenCells() {
    for (const spawn of bidenSpawns) {
      spawn.cell = targetToCell(spawn.normX, spawn.normY);
    }
  }

  function addSpawn(payload) {
    if (!payload) return;
    if (payload.type === "reload_overlay") {
      window.location.reload();
      return;
    }
    if (payload.type === "spawn_biden") {
      addBidenSpawn(payload);
      resetBidenTimer(performance.now());
      return;
    }
    if (payload.type === "spawn_worm") {
      queuePoopWormSpawn(performance.now());
      // return;
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
    if (config.logOnly && speaker !== "gm") return;
    combatLog.push({ speaker, text, startedAt: now, channel });
    while (combatLog.length > 18) {
      combatLog.shift();
    }
  }

  function addHudMessage(payload, now) {
    const text = String(payload.text || "").trim();
    if (!text) return false;
    const ttlMs = positiveNumber(payload.ttl_ms, defaultHudMessageTtlMs);
    const repeatIntervalMs = positiveNumber(payload.repeat_interval_ms, 0);
    const id = payload.event_id || `hud:${now}:${hudMessages.length}`;
    const existing = hudMessages.find((message) => message.id === id);
    if (existing) {
      existing.text = text.slice(0, 500);
      existing.ttlMs = ttlMs;
      existing.repeatIntervalMs = repeatIntervalMs;
      existing.displayedAt = now;
      existing.expiresAt = now + ttlMs;
      existing.nextRepeatAt = repeatIntervalMs > 0 ? now + repeatIntervalMs : 0;
      return true;
    }
    hudMessages.push({
      id,
      text: text.slice(0, 500),
      ttlMs,
      repeatIntervalMs,
      displayedAt: now,
      expiresAt: now + ttlMs,
      nextRepeatAt: repeatIntervalMs > 0 ? now + repeatIntervalMs : 0,
    });
    while (hudMessages.length > 24) {
      hudMessages.shift();
    }
    return true;
  }

  function deleteHudMessage(payload) {
    const id = String(payload.event_id || "").trim();
    if (!id) return false;
    for (let i = hudMessages.length - 1; i >= 0; i -= 1) {
      if (hudMessages[i].id === id) {
        hudMessages.splice(i, 1);
      }
    }
    return true;
  }

  function updateBidenTimer(payload, now) {
    bidenTimer.available = Boolean(payload.available);
    bidenTimer.remainingSeconds = bidenTimer.available ? positiveNumber(payload.remaining_seconds, 0) : null;
    bidenTimer.receivedAt = now;
    bidenTimer.onScreen = Number(payload.on_screen || 0);
    bidenTimer.resetAt = 0;
  }

  function resetBidenTimer(now) {
    bidenTimer.available = true;
    bidenTimer.remainingSeconds = 0;
    bidenTimer.receivedAt = now;
    bidenTimer.resetAt = now;
  }

  function positiveNumber(value, fallback) {
    const numeric = Number(value);
    return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback;
  }

  function handleBidenEaten(spawn, now) {
    spawn.beingEaten = true;
    spawn.eatenAt = now;
    snake.eatenCount += 1;
    maybeAddFakeCursorEatQuip(now);
    snake.hp = Math.min(snake.maxHp, snake.hp + 25);
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

  function maybeAddFakeCursorEatQuip(now) {
    if (snake.eatenCount % 6 !== 3) return;
    addCombatLogLine("FakeCursor", "Is it just me, or is granda looking thick?", now);
  }

  function updateEnrageState(now) {
    if (snake.dead) return;
    if (!snake.enraged) return;
    if (now < snake.enrageStart + snake.enrageDuration) return;
    snake.enraged = false;
    snake.enrageEndedAt = now;
    snake.enrageStart = 0;
    snake.enrageEatenCount = 0;
    spawnBabyGrandmaSnake(now);
    addCombatLogLine("grandma", "Enrage spent.", now);
  }

  function spawnBabyGrandmaSnake(now) {
    const totalGrandmas = (snake.dead ? 0 : 1) + babyGrandmaSnakes.length;
    if (totalGrandmas >= grandmaMaxCount) return;
    if (now - lastGrandmaSpawnTime < grandmaSpawnSpacingMs) return;
    lastGrandmaSpawnTime = now;
    const parentHead = snake.heatSegments[0] || cellToPixel({
      x: Math.floor(gridWidth() / 2),
      y: Math.floor(gridHeight() / 2),
    });
    const angle = Math.random() * Math.PI * 2;
    const distance = cellSize * (1.2 + Math.random() * 1.4);
    const head = clampHeatPointToViewport({
      x: parentHead.x + Math.cos(angle) * distance,
      y: parentHead.y + Math.sin(angle) * distance,
    });
    const direction = normalizeVector({
      x: Math.cos(angle + Math.PI / 2),
      y: Math.sin(angle + Math.PI / 2),
    });
    babyGrandmaSnakes.push({
      heatSegments: [head],
      heatDirection: direction,
      lastFrame: now,
      heatTargeting: false,
      heatStuckSample: null,
      heatStuckSince: 0,
      heatRecoveryUntil: 0,
      spawnedAt: now,
      maxHp: grandmaMaxHp,
      hp: grandmaMaxHp,
      dead: false,
    });
    addCombatLogLine("grandma", "A baby Grandma joins the hunt.", now + 150);
  }

  function spawnBabyGrandmaSnakeFromPoop(origin, direction, now, drawScale) {
    const totalGrandmas = (snake.dead ? 0 : 1) + babyGrandmaSnakes.length;
    if (totalGrandmas >= grandmaMaxCount) return;
    if (now - lastGrandmaSpawnTime < grandmaSpawnSpacingMs) return;
    lastGrandmaSpawnTime = now;
    const head = clampHeatPointToViewport(origin);
    const tailDirection = normalizeVector({
      x: -direction.x,
      y: -direction.y,
    });
    babyGrandmaSnakes.push({
      heatSegments: [
        head,
        clampHeatPointToViewport({
          x: head.x + tailDirection.x * cellSize * 0.75,
          y: head.y + tailDirection.y * cellSize * 0.75,
        }),
      ],
      heatDirection: normalizeVector(direction),
      lastFrame: now,
      heatTargeting: false,
      heatStuckSample: null,
      heatStuckSince: 0,
      heatRecoveryUntil: 0,
      spawnedAt: now,
      maxHp: grandmaMaxHp,
      hp: grandmaMaxHp,
      dead: false,
      drawScale: drawScale,
      speedMultiplier: babyGrandmaSpeedMultiplier,
    });
    addCombatLogLine("grandma", "A baby Grandma spawns from the poop.", now + 150);
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
    if (!snake.dead) {
      updateEnrageState(now);
      enterHeatSeekingMode(now);
      advanceHeatSeeking(now);
    }
    advanceBabyGrandmaSnakes(now);
    maybeDropGrandmaPoops(now);
    advanceGrandmaPoops(now);
    advancePoopWorms(now);
    maybeSpawnSuperGrandmaFromHungryWorms(now);
    updateGrandmaSnakePresence(now);
    maybeSpawnSuperSnakesDueToTimeout(now);
    manageWormLimit(now);
    advanceFlies(now);
  }

  function advanceBabyGrandmaSnakes(now) {
    for (const baby of babyGrandmaSnakes.slice()) {
      if (baby.dead) continue;
      advanceHeatSnake(baby, now, {
        announceTargeting: false,
        speedMultiplier: baby.speedMultiplier || babyGrandmaSpeedMultiplier,
      });
    }
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
    advanceHeatSnake(snake, now, {
      announceTargeting: true,
      speedMultiplier: 1,
    });
  }

  function advanceHeatSnake(heatSnake, now, options = {}) {
    if (heatSnake.heatSegments.length === 0) {
      heatSnake.heatSegments = gridSegmentsToPixels(interpolatedSegments(now));
    }

    const dt = Math.min(80, Math.max(0, now - (heatSnake.lastFrame || now)));
    heatSnake.lastFrame = now;
    const head = heatSnake.heatSegments[0];
    const target = nearestHeatTarget(head, heatSnake);
    if (target && !heatSnake.heatTargeting && options.announceTargeting) {
      addCombatLogLine("grandma", "Heat seeking mode engage!", now);
    }
    heatSnake.heatTargeting = Boolean(target);
    if (eatHeatTargetIfReached(heatSnake, head, target, now)) {
      relaxHeatTail(heatSnake);
      return;
    }
    const speed = (cellSize / snakeTickMs) * enrageMovementMultiplier(now) * (options.speedMultiplier || 1);
    const maxStep = speed * dt;
    const sizes = segmentSizeMultipliers(heatSnake.heatSegments.length);
    const targetPoint = target ? heatTargetPoint(target) : null;
    let desired = target
      ? vectorToward(head, targetPoint)
      : heatSnake.heatDirection;

    if (!target) {
      desired = bounceHeatDirection(head, desired);
    }
    if (targetPoint) {
      desired = normalizeVector(addVectors(desired, targetMagnetVector(head, targetPoint)));
    }
    desired = normalizeVector(addVectors(desired, wallEscapeVector(head, targetPoint)));
    if (heatSnake.heatRecoveryUntil > now) {
      desired = normalizeVector(addVectors(desired, scaleVector(inwardWallVector(head), 4.5)));
    }

    const previousHead = { x: head.x, y: head.y };
    const chosenMove = chooseHeatMove(head, desired, maxStep, sizes, targetPoint, heatSnake);
    head.x = chosenMove.x;
    head.y = chosenMove.y;
    heatSnake.heatDirection = chosenMove.direction;
    clampHeatSegmentsToViewport(heatSnake);
    if (updateHeatStuckState(previousHead, head, now, heatSnake) || heatSnake.heatRecoveryUntil > now) {
      applyHeatStuckRecovery(head, sizes, maxStep, now, heatSnake);
    }

    eatHeatTargetIfReached(heatSnake, head, target, now);

    relaxHeatTail(heatSnake);
  }

  function eatHeatTargetIfReached(heatSnake, head, target, now) {
    if (!target || heatTargetBeingEaten(target)) return false;
    if (heatTargetDistance(head, target) > bidenEatRadius) return false;
    const tail = heatSnake.heatSegments[heatSnake.heatSegments.length - 1] || head;
    heatSnake.heatSegments.push({ x: tail.x, y: tail.y });
    handleHeatTargetEaten(target, now);
    return true;
  }

  function updateHeatStuckState(previousHead, head, now, heatSnake = snake) {
    if (heatWallContactCount(head) === 0) {
      heatSnake.heatStuckSample = null;
      heatSnake.heatStuckSince = 0;
      return false;
    }

    const movedThisFrame = pixelDistance(previousHead, head);
    if (movedThisFrame > cellSize * 0.18) {
      heatSnake.heatStuckSample = { x: head.x, y: head.y, at: now };
      heatSnake.heatStuckSince = 0;
      return false;
    }

    if (!heatSnake.heatStuckSample || pixelDistance(heatSnake.heatStuckSample, head) > cellSize * 0.45) {
      heatSnake.heatStuckSample = { x: head.x, y: head.y, at: now };
      heatSnake.heatStuckSince = 0;
      return false;
    }

    const pinnedMs = now - heatSnake.heatStuckSample.at;
    if (pinnedMs < 650) return false;
    if (!heatSnake.heatStuckSince) heatSnake.heatStuckSince = now;
    heatSnake.heatRecoveryUntil = Math.max(heatSnake.heatRecoveryUntil, now + 900);
    heatSnake.heatStuckSample = { x: head.x, y: head.y, at: now };
    return true;
  }

  function applyHeatStuckRecovery(head, sizes, maxStep, now, heatSnake = snake) {
    const inward = inwardWallVector(head);
    if (Math.abs(inward.x) <= 0.001 && Math.abs(inward.y) <= 0.001) return;

    const recoveryProgress = Math.max(0, Math.min(1, (heatSnake.heatRecoveryUntil - now) / 900));
    const headStep = Math.max(maxStep, cellSize * (0.28 + recoveryProgress * 0.16));
    const recoveredHead = clampHeatPointToViewport({
      x: head.x + inward.x * headStep,
      y: head.y + inward.y * headStep,
    });
    head.x = recoveredHead.x;
    head.y = recoveredHead.y;
    heatSnake.heatDirection = inward;

    for (let i = 1; i < heatSnake.heatSegments.length; i += 1) {
      const segment = heatSnake.heatSegments[i];
      const awayFromHead = vectorAwayFrom(head, segment, inward);
      const falloff = Math.max(0.2, 1 - (i / Math.max(2, heatSnake.heatSegments.length)));
      const push = cellSize * 0.42 * falloff;
      const moved = clampHeatPointToViewport({
        x: segment.x + inward.x * push + awayFromHead.x * push * 0.85,
        y: segment.y + inward.y * push + awayFromHead.y * push * 0.85,
      });
      segment.x = moved.x;
      segment.y = moved.y;
    }
    clampHeatSegmentsToViewport(heatSnake);
  }

  function nearestHeatTarget(head, heatSnake = snake) {
    const activeBidens = activeBidenSpawns();
    let best = null;
    let bestDistance = Infinity;
    for (const spawn of activeBidens) {
      const distance = pixelDistance(head, bidenCenter(spawn));
      if (distance < bestDistance) {
        best = spawn;
        bestDistance = distance;
      }
    }
    if (heatSnake && heatSnake.canEatFlies) {
      for (const fly of flies) {
        if (fly.state === "falling" || fly.state === "fallen" || fly.beingEaten) continue;
        const distance = pixelDistance(head, fly);
        if (distance < bestDistance) {
          best = { kind: "fly", fly };
          bestDistance = distance;
        }
      }
    }
    return best;
  }

  function heatTargetPoint(target) {
    if (target && target.kind === "fly") {
      return { x: target.fly.x, y: target.fly.y };
    }
    return bidenCenter(target);
  }

  function heatTargetDistance(point, target) {
    if (target && target.kind === "fly") {
      return pixelDistance(point, target.fly);
    }
    return bidenHitDistance(point, target);
  }

  function heatTargetBeingEaten(target) {
    if (target && target.kind === "fly") {
      return Boolean(target.fly.beingEaten);
    }
    return Boolean(target && target.beingEaten);
  }

  function handleHeatTargetEaten(target, now) {
    if (target && target.kind === "fly") {
      handleFlyEaten(target.fly, now);
      return;
    }
    handleBidenEaten(target, now);
  }

  function handleFlyEaten(fly, now) {
    if (!fly || fly.beingEaten) return;
    fly.beingEaten = true;
    const index = flies.indexOf(fly);
    if (index >= 0) flies.splice(index, 1);
    playSound(sounds.grandma);
    addCombatLogLine("grandma", "Super Grandma ate a fly.", now);
  }

  function bidenHitDistance(point, spawn) {
    return pixelDistance(point, bidenCenter(spawn));
  }

  function targetMagnetVector(head, targetPoint) {
    const distance = pixelDistance(head, targetPoint);
    if (distance >= bidenCloseRange) return { x: 0, y: 0 };
    const pull = vectorToward(head, targetPoint);
    const closeness = 1 - (distance / bidenCloseRange);
    return scaleVector(pull, 0.8 + closeness * 2.8);
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

  function chooseHeatMove(origin, desired, maxStep, sizes, targetPoint, heatSnake = snake) {
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
      const score = scoreHeatMove(origin, point, actualDirection, baseDirection, sizes, targetPoint, heatSnake);
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

  function scoreHeatMove(origin, point, direction, baseDirection, sizes, targetPoint, heatSnake = snake) {
    const wallMargin = heatWallMargin(point);
    const turnPenalty = (1 - Math.max(-1, Math.min(1, direction.x * baseDirection.x + direction.y * baseDirection.y))) * 14;
    const movement = pixelDistance(origin, point);
    const targetDistance = targetPoint ? pixelDistance(point, targetPoint) : 0;
    const targetGain = targetPoint
      ? pixelDistance(origin, targetPoint) - pixelDistance(point, targetPoint)
      : 0;
    const closeTargetBonus = targetPoint && targetDistance < bidenCloseRange
      ? (bidenCloseRange - targetDistance) * 2.4
      : 0;
    const wallPenalty = wallEscapeMagnitude(point) * 22;
    const outwardPenalty = outwardWallPressure(origin, direction) * 120;

    return wallMargin * 0.25 + movement * 2 + targetGain * 6 + closeTargetBonus - turnPenalty - wallPenalty - outwardPenalty;
  }

  function wallEscapeMagnitude(point) {
    const escape = wallEscapeVector(point, null);
    return Math.sqrt(escape.x * escape.x + escape.y * escape.y);
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

  function relaxHeatTail(heatSnake = snake) {
    const sizes = segmentSizeMultipliers(heatSnake.heatSegments.length);
    for (let i = 1; i < heatSnake.heatSegments.length; i += 1) {
      const leader = heatSnake.heatSegments[i - 1];
      const follower = heatSnake.heatSegments[i];
      const spacing = heatSegmentSpacing(i - 1, i, sizes);
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

  class AsepriteBoneSprite {
    constructor(url, options = {}) {
      this.url = url;
      this.manifestUrl = options.manifestUrl || "";
      this.imageLayerName = options.imageLayerName || "worm";
      this.bonesLayerName = options.bonesLayerName || "bones";
      this.sliceCount = options.sliceCount || 56;
      this.width = 0;
      this.height = 0;
      this.imageCanvas = null;
      this.bonesCanvas = null;
      this.restPoints = [];
      this.minBoneX = 0;
      this.maxBoneX = 0;
      this.boneBaseY = 0;
      this.opaqueBottomY = 0;
      this.ready = false;
    }

    async load() {
      if (this.manifestUrl) {
        await this.loadExtractedLayers();
        this.ready = true;
        return this;
      }
      const response = await fetch(`${this.url}?v=${assetVersion}`);
      if (!response.ok) throw new Error(`Could not load Aseprite sprite: ${this.url}`);
      const buffer = await response.arrayBuffer();
      await this.parse(buffer);
      this.ready = true;
      return this;
    }

    async loadExtractedLayers() {
      const response = await fetch(`${this.manifestUrl}?v=${assetVersion}`);
      if (!response.ok) throw new Error(`Could not load bone sprite manifest: ${this.manifestUrl}`);
      const manifest = await response.json();
      this.width = Number(manifest.width || 0);
      this.height = Number(manifest.height || 0);
      const layers = manifest.layers || {};
      const imageUrl = layers[this.imageLayerName];
      const bonesUrl = layers[this.bonesLayerName];
      if (!imageUrl || !bonesUrl || this.width <= 0 || this.height <= 0) {
        throw new Error(`Bone sprite manifest is missing ${this.imageLayerName}/${this.bonesLayerName} layers`);
      }
      this.imageCanvas = await imageCanvasFromUrl(imageUrl, this.width, this.height);
      this.bonesCanvas = await imageCanvasFromUrl(bonesUrl, this.width, this.height);
      this.extractImageAlphaBounds();
      this.extractRestBones();
    }

    async parse(buffer) {
      const view = new DataView(buffer);
      const bytes = new Uint8Array(buffer);
      if (view.getUint16(4, true) !== 0xA5E0) {
        throw new Error(`Unsupported Aseprite file magic for ${this.url}`);
      }
      this.width = view.getUint16(8, true);
      this.height = view.getUint16(10, true);
      const colorDepth = view.getUint16(12, true);
      if (colorDepth !== 32) {
        throw new Error(`Only RGBA Aseprite files are supported for ${this.url}`);
      }

      const layers = [];
      const layerCanvases = new Map();
      let offset = 128;
      const frameCount = view.getUint16(6, true);
      for (let frame = 0; frame < frameCount; frame += 1) {
        const frameBytes = view.getUint32(offset, true);
        const oldChunkCount = view.getUint16(offset + 6, true);
        const newChunkCount = view.getUint32(offset + 16, true);
        const chunkCount = newChunkCount || oldChunkCount;
        let chunkOffset = offset + 16;
        for (let chunk = 0; chunk < chunkCount; chunk += 1) {
          const chunkSize = view.getUint32(chunkOffset, true);
          const chunkType = view.getUint16(chunkOffset + 4, true);
          const payload = chunkOffset + 6;
          if (chunkType === 0x2004) {
            const opacity = view.getUint8(payload + 12);
            const nameLength = view.getUint16(payload + 16, true);
            const nameBytes = bytes.slice(payload + 18, payload + 18 + nameLength);
            layers.push({
              name: new TextDecoder().decode(nameBytes),
              opacity,
            });
          } else if (chunkType === 0x2005) {
            await this.parseCelChunk(view, bytes, payload, layers, layerCanvases);
          }
          chunkOffset += chunkSize;
        }
        offset += frameBytes;
      }

      this.imageCanvas = layerCanvases.get(this.imageLayerName);
      this.bonesCanvas = layerCanvases.get(this.bonesLayerName);
      if (!this.imageCanvas || !this.bonesCanvas) {
        throw new Error(`Aseprite sprite must contain ${this.imageLayerName} and ${this.bonesLayerName} layers`);
      }
      this.extractImageAlphaBounds();
      this.extractRestBones();
    }

    async parseCelChunk(view, bytes, payload, layers, layerCanvases) {
      const layerIndex = view.getUint16(payload, true);
      const layer = layers[layerIndex];
      if (!layer) return;
      if (layer.name !== this.imageLayerName && layer.name !== this.bonesLayerName) return;

      const x = view.getInt16(payload + 2, true);
      const y = view.getInt16(payload + 4, true);
      const opacity = view.getUint8(payload + 6) / 255;
      const celType = view.getUint16(payload + 7, true);
      if (celType !== 0 && celType !== 2) return;

      const celWidth = view.getUint16(payload + 16, true);
      const celHeight = view.getUint16(payload + 18, true);
      const pixelOffset = payload + 20;
      const pixelByteLength = celWidth * celHeight * 4;
      let pixels;
      if (celType === 2) {
        pixels = await inflateAsepriteZlib(bytes.slice(pixelOffset, payload + view.getUint32(payload - 6, true) - 6));
      } else {
        pixels = bytes.slice(pixelOffset, pixelOffset + pixelByteLength);
      }
      if (pixels.length < pixelByteLength) return;

      const canvasForLayer = layerCanvases.get(layer.name) || createLayerCanvas(this.width, this.height);
      layerCanvases.set(layer.name, canvasForLayer);
      const layerCtx = canvasForLayer.getContext("2d");
      const imageData = new ImageData(new Uint8ClampedArray(pixels.slice(0, pixelByteLength)), celWidth, celHeight);
      const celCanvas = createLayerCanvas(celWidth, celHeight);
      celCanvas.getContext("2d").putImageData(imageData, 0, 0);
      layerCtx.save();
      layerCtx.globalAlpha = opacity * (layer.opacity / 255);
      layerCtx.drawImage(celCanvas, x, y);
      layerCtx.restore();
    }

    extractRestBones() {
      const imageData = this.bonesCanvas.getContext("2d").getImageData(0, 0, this.width, this.height).data;
      const columns = [];
      for (let x = 0; x < this.width; x += 1) {
        let totalY = 0;
        let count = 0;
        for (let y = 0; y < this.height; y += 1) {
          const index = (y * this.width + x) * 4;
          const r = imageData[index];
          const g = imageData[index + 1];
          const b = imageData[index + 2];
          const a = imageData[index + 3];
          if (a > 16 && r > 190 && b > 190 && g < 90) {
            totalY += y;
            count += 1;
          }
        }
        if (count > 0) columns.push({ x, y: totalY / count });
      }

      if (columns.length < 2) {
        this.minBoneX = 0;
        this.maxBoneX = this.width;
        this.boneBaseY = this.height / 2;
        this.restPoints = Array.from({ length: this.sliceCount + 1 }, (_, i) => ({
          x: (i / this.sliceCount) * this.width,
          y: this.boneBaseY,
        }));
        return;
      }

      this.minBoneX = columns[0].x;
      this.maxBoneX = columns[columns.length - 1].x;
      this.boneBaseY = columns.reduce((sum, point) => sum + point.y, 0) / columns.length;
      this.restPoints = [];
      for (let i = 0; i <= this.sliceCount; i += 1) {
        const x = this.minBoneX + ((this.maxBoneX - this.minBoneX) * i) / this.sliceCount;
        this.restPoints.push({ x, y: interpolateBoneColumn(columns, x) });
      }
    }

    extractImageAlphaBounds() {
      const imageData = this.imageCanvas.getContext("2d").getImageData(0, 0, this.width, this.height).data;
      let bottom = 0;
      for (let y = 0; y < this.height; y += 1) {
        for (let x = 0; x < this.width; x += 1) {
          if (imageData[(y * this.width + x) * 4 + 3] > 16) {
            bottom = Math.max(bottom, y);
          }
        }
      }
      this.opaqueBottomY = bottom;
    }

    buildWavePose(options) {
      const x = options.x || 0;
      const y = options.y || 0;
      const scale = options.scale || 1;
      const direction = options.direction >= 0 ? 1 : -1;
      const phase = options.phase || 0;
      const amplitude = (options.amplitude || 5.5) * scale;
      const cycles = options.cycles || 2.25;
      const length = Math.max(1, this.maxBoneX - this.minBoneX);
      return this.restPoints.map((point) => {
        const t = (point.x - this.minBoneX) / length;
        return {
          x: x + direction * (point.x - this.minBoneX) * scale,
          y: y + Math.sin(t * Math.PI * 2 * cycles + phase) * amplitude,
        };
      });
    }

    buildInchwormPose(options) {
      const x = options.x || 0;
      const y = options.y || 0;
      const scale = options.scale || 1;
      const direction = options.direction >= 0 ? 1 : -1;
      const phase = options.phase || 0;
      const length = Math.max(1, this.maxBoneX - this.minBoneX);
      const contraction = (1 - Math.cos(phase)) / 2;
      const lengthFactor = 1 - contraction * (options.contraction || 0.3);
      const arch = (options.arch || 18) * scale * contraction;
      const headShake = (options.headShake || 0) * scale;
      const headShakePhase = options.headShakePhase || phase;

      return this.restPoints.map((point) => {
        const t = (point.x - this.minBoneX) / length;
        const localX = t * length * lengthFactor;
        const archShape = Math.sin(t * Math.PI);
        const bodyArch = Math.pow(Math.max(0, archShape), 1.45) * arch;
        const bodyRipple = Math.sin(phase * 1.2 + t * Math.PI * 2) * scale * 0.45;
        const headWeight = Math.max(0, Math.min(1, (t - 0.78) / 0.22));
        const headShakeX = Math.sin(headShakePhase * 2.4) * headShake * headWeight * 0.28;
        const headShakeY = Math.cos(headShakePhase * 3.2) * headShake * headWeight;
        return {
          x: x + direction * (localX + headShakeX),
          y: y - bodyArch + bodyRipple + headShakeY,
        };
      });
    }

    mouthPoint(pose) {
      return pose[pose.length - 1] || { x: 0, y: 0 };
    }

    lengthAtScale(scale) {
      return Math.max(1, (this.maxBoneX - this.minBoneX) * scale);
    }

    groundBaselineY(groundY, scale) {
      return groundY - (this.opaqueBottomY - this.boneBaseY) * scale;
    }

    poseDrawBounds(pose, scale) {
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;
      for (let i = 0; i < pose.length - 1; i += 1) {
        const p0 = pose[i];
        const p1 = pose[i + 1];
        const sourceBoneY = this.restPoints[i].y;
        const facingLeft = p1.x < p0.x;
        const segmentStart = facingLeft ? p1 : p0;
        const segmentEnd = facingLeft ? p0 : p1;
        const dx = segmentEnd.x - segmentStart.x;
        const dy = segmentEnd.y - segmentStart.y;
        const segmentLength = Math.sqrt(dx * dx + dy * dy);
        if (segmentLength < 0.01) continue;
        const sin = dy / segmentLength;
        const cos = dx / segmentLength;
        const localTop = -sourceBoneY * scale;
        const localBottom = (this.opaqueBottomY - sourceBoneY) * scale;
        const localStart = facingLeft ? -segmentLength : 0;
        const localEnd = facingLeft ? 0 : segmentLength;
        const corners = [
          transformSpriteLocalPoint(segmentStart, cos, sin, localStart, localTop, facingLeft),
          transformSpriteLocalPoint(segmentStart, cos, sin, localEnd, localTop, facingLeft),
          transformSpriteLocalPoint(segmentStart, cos, sin, localStart, localBottom, facingLeft),
          transformSpriteLocalPoint(segmentStart, cos, sin, localEnd, localBottom, facingLeft),
        ];
        for (const corner of corners) {
          minX = Math.min(minX, corner.x);
          maxX = Math.max(maxX, corner.x);
          minY = Math.min(minY, corner.y);
          maxY = Math.max(maxY, corner.y);
        }
      }
      return {
        minX: Number.isFinite(minX) ? minX : 0,
        maxX: Number.isFinite(maxX) ? maxX : 0,
        minY: Number.isFinite(minY) ? minY : 0,
        maxY: Number.isFinite(maxY) ? maxY : 0,
      };
    }

    draw(ctx, pose, options = {}) {
      if (!this.ready || pose.length < 2) return;
      const scale = options.scale || 1;
      ctx.save();
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      for (let i = 0; i < pose.length - 1; i += 1) {
        const p0 = pose[i];
        const p1 = pose[i + 1];
        const sourceX = this.restPoints[i].x;
        const nextSourceX = this.restPoints[i + 1].x;
        const sourceOverlap = 2;
        const overlappedSourceX = Math.max(0, sourceX - sourceOverlap);
        const sourceWidth = Math.min(this.width - overlappedSourceX, Math.max(1, nextSourceX - sourceX + 1 + sourceOverlap * 2));
        const sourceBoneY = this.restPoints[i].y;
        const facingLeft = p1.x < p0.x;
        const segmentStart = facingLeft ? p1 : p0;
        const segmentEnd = facingLeft ? p0 : p1;
        const dx = segmentEnd.x - segmentStart.x;
        const dy = segmentEnd.y - segmentStart.y;
        const segmentLength = Math.sqrt(dx * dx + dy * dy);
        if (segmentLength < 0.01) continue;
        const destOverlap = Math.max(3, scale * 2.5);

        ctx.save();
        ctx.translate(segmentStart.x, segmentStart.y);
        ctx.rotate(Math.atan2(dy, dx));
        if (facingLeft) ctx.scale(-1, 1);
        ctx.drawImage(
          this.imageCanvas,
          overlappedSourceX,
          0,
          sourceWidth,
          this.height,
          facingLeft ? -segmentLength - destOverlap / 2 : -destOverlap / 2,
          -sourceBoneY * scale,
          segmentLength + destOverlap,
          this.height * scale,
        );
        ctx.restore();
      }
      ctx.restore();
    }
  }

  async function inflateAsepriteZlib(bytes) {
    if (typeof DecompressionStream === "undefined") {
      throw new Error("This browser does not support DecompressionStream for Aseprite layer data.");
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  function createLayerCanvas(width, height) {
    const layerCanvas = document.createElement("canvas");
    layerCanvas.width = width;
    layerCanvas.height = height;
    return layerCanvas;
  }

  async function imageCanvasFromUrl(url, width, height) {
    const image = await loadImage(url);
    const layerCanvas = createLayerCanvas(width || image.naturalWidth, height || image.naturalHeight);
    layerCanvas.getContext("2d").drawImage(image, 0, 0);
    return layerCanvas;
  }

  function loadImage(url) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`Could not load image: ${url}`));
      image.src = `${url}?v=${assetVersion}`;
    });
  }

  function transformLocalPoint(origin, cos, sin, x, y) {
    return {
      x: origin.x + x * cos - y * sin,
      y: origin.y + x * sin + y * cos,
    };
  }

  function transformSpriteLocalPoint(origin, cos, sin, x, y, mirrored) {
    return transformLocalPoint(origin, cos, sin, mirrored ? -x : x, y);
  }

  function interpolateBoneColumn(columns, x) {
    if (x <= columns[0].x) return columns[0].y;
    for (let i = 1; i < columns.length; i += 1) {
      if (x <= columns[i].x) {
        const previous = columns[i - 1];
        const next = columns[i];
        const t = (x - previous.x) / Math.max(1, next.x - previous.x);
        return previous.y + (next.y - previous.y) * t;
      }
    }
    return columns[columns.length - 1].y;
  }

  function maybeDropGrandmaPoops(now) {
    if (!lastGrandmaPoopAt) lastGrandmaPoopAt = now;
    
    // Super grandmas poop three times as often
    const superGrandmas = babyGrandmaSnakes.filter(b => b.drawScale > babyGrandmaDrawScale);
    const dropInterval = superGrandmas.length > 0 ? poopDropIntervalMs / 3 : poopDropIntervalMs;
    if (now - lastGrandmaPoopAt < dropInterval) return;
    lastGrandmaPoopAt = now;

    const hasGrandmas = !snake.dead || babyGrandmaSnakes.length > 0;
    if (!hasGrandmas && !pendingWormBecomingSuperGrandma) {
      const canSummonWorm = totalGrandmaPoopsSpawned > 0 && totalGrandmaPoopsSpawned % wormSpawnEveryPoops === 0;
      const hasPoop = grandmaPoops.length > 0;
      if (!canSummonWorm || !hasPoop) {
        queuePoopWormSpawn(now);
        pendingWormBecomingSuperGrandma = true;
      }
    }

    if (!snake.dead) {
      spawnGrandmaPoop(snake, now, 1);
    }
    for (const baby of babyGrandmaSnakes) {
      if (baby.dead) continue;
      spawnGrandmaPoop(baby, now, baby.drawScale || babyGrandmaDrawScale);
    }

    const poopsThisTick = (snake.dead ? 0 : 1) + babyGrandmaSnakes.filter(b => !b.dead).length;
    const prevTotal = totalGrandmaPoopsSpawned;
    totalGrandmaPoopsSpawned += poopsThisTick;
    for (let i = prevTotal + 1; i <= totalGrandmaPoopsSpawned; i++) {
      if (i % wormSpawnEveryPoops === 0) {
        queuePoopWormSpawn(now);
        break;
      }
    }
  }

  function spawnGrandmaPoop(grandmaSnake, now, drawScale) {
    const segments = currentGrandmaSegments(grandmaSnake, now);
    if (segments.length === 0) return false;

    const tailIndex = segments.length - 1;
    const tail = segments[tailIndex];
    const tailDirection = grandmaTailDirection(grandmaSnake, segments);
    const sizes = segmentSizeMultipliers(segments.length);
    const baseSize = tailIndex === 0 ? snakeHeadDrawSize : snakeBodyDrawSize;
    const tailRadius = (baseSize * sizes[tailIndex] * drawScale) / 2;
    const startSize = poopDrawSize * Math.max(0.45, drawScale);
    const startX = tail.x + tailDirection.x * tailRadius * 0.65;
    const startY = tail.y + tailDirection.y * tailRadius * 0.65;

    const hasGrandmas = !snake.dead || babyGrandmaSnakes.length > 0;
    const isFinalPoop = grandmaPoops.length === 0 && !hasGrandmas;
    const isSuperGrandma = drawScale > babyGrandmaDrawScale;
    const isGrandmaEnraged = isSuperGrandma && isEnraged(now);
    if (isFinalPoop || (!isSuperGrandma && Math.random() < superGrandmaPoopChance) || isGrandmaEnraged) {
      const onlySuperGrandma = !isSuperGrandma && babyGrandmaSnakes.length > 0 && babyGrandmaSnakes.every(b => b.drawScale > babyGrandmaDrawScale);
      if (isGrandmaEnraged && !isFinalPoop && (Math.random() < 0.5 || onlySuperGrandma)) {
        spawnSuperGrandmaSnake({ x: startX, y: startY }, tailDirection, now);
      } else {
        spawnBabyGrandmaSnakeFromPoop({ x: startX, y: startY }, tailDirection, now, drawScale);
      }
      playSound(sounds.poop);
      return true;
    }

    grandmaPoops.push({
      x: startX,
      y: startY,
      vx: tailDirection.x * poopTailImpulse + (Math.random() - 0.5) * 30,
      vy: tailDirection.y * poopTailImpulse - 35,
      angle: Math.atan2(tailDirection.y, tailDirection.x) + Math.PI / 2,
      angularVelocity: (Math.random() - 0.5) * 4.8,
      size: startSize,
      createdAt: now,
      lastFrameAt: now,
      eatScale: 1,
      eatShake: 0,
      beingEaten: false,
      floorContactSince: 0,
      dissolving: false,
      dissolveStartedAt: 0,
      dissolveProgress: 0,
      dissolveScale: 1,
    });
    if (grandmaPoops.length > 80) grandmaPoops.shift();
    playSound(sounds.poop);
    return true;
  }

  function spawnSuperGrandmaSnake(origin, direction, now) {
    const totalGrandmas = (snake.dead ? 0 : 1) + babyGrandmaSnakes.length;
    if (totalGrandmas >= grandmaMaxCount) return false;
    if (now - lastGrandmaSpawnTime < grandmaSpawnSpacingMs) return false;
    // Limit to 2 super grandmas at a time
    const superGrandmas = babyGrandmaSnakes.filter(b => b.drawScale > babyGrandmaDrawScale);
    if (superGrandmas.length >= 2) return false;
    
    lastGrandmaSpawnTime = now;
    const head = clampHeatPointToViewport(origin);
    const tailDirection = normalizeVector({
      x: -direction.x,
      y: -direction.y,
    });
    babyGrandmaSnakes.push({
      heatSegments: [
        head,
        clampHeatPointToViewport({
          x: head.x + tailDirection.x * cellSize * 0.75,
          y: head.y + tailDirection.y * cellSize * 0.75,
        }),
      ],
      heatDirection: normalizeVector(direction),
      lastFrame: now,
      heatTargeting: false,
      heatStuckSample: null,
      heatStuckSince: 0,
      heatRecoveryUntil: 0,
      spawnedAt: now,
      maxHp: grandmaMaxHp,
      hp: grandmaMaxHp,
      dead: false,
      canEatFlies: true,
      drawScale: superGrandmaDrawScale,
      speedMultiplier: superGrandmaSpeedMultiplier,
    });
    addCombatLogLine("grandma", "A super Grandma snake bursts from the poop.", now + 150, "shout");
    return true;
  }

   function wormBecameSuperGrandmaSnake(worm, now) {
     if (!pendingWormBecomingSuperGrandma) return false;
     pendingWormBecomingSuperGrandma = false;
     const origin = { x: worm.x, y: worm.baselineY - 30 };
     const direction = { x: worm.direction, y: 0 };
     // Remove worm from array before spawning super grandma
     const wormIndex = poopWorms.indexOf(worm);
     if (wormIndex >= 0) {
       poopWorms.splice(wormIndex, 1);
     }
     spawnSuperGrandmaSnake(origin, direction, now);
     return true;
   }

  function currentGrandmaSegments(grandmaSnake, now) {
    if (grandmaSnake.heatSegments && grandmaSnake.heatSegments.length > 0) {
      return grandmaSnake.heatSegments;
    }
    if (grandmaSnake === snake && snake.segments.length > 0) {
      return gridSegmentsToPixels(interpolatedSegments(now));
    }
    return [];
  }

  function grandmaTailDirection(grandmaSnake, segments) {
    const tailIndex = segments.length - 1;
    if (tailIndex <= 0) {
      const direction = grandmaSnake.heatDirection || snake.heatDirection || { x: 1, y: 0 };
      return normalizeVector({ x: -direction.x, y: -direction.y });
    }

    const tail = segments[tailIndex];
    const previous = segments[tailIndex - 1];
    return normalizeVector({
      x: tail.x - previous.x,
      y: tail.y - previous.y,
    });
  }

  function advanceGrandmaPoops(now) {
    // Start dissolving poops that have exceeded their time to live
    for (const poop of grandmaPoops) {
      if (poop.beingEaten || poop.dissolving) continue;
      if (now - poop.createdAt >= poopTimeToLiveMs) {
        beginPoopDissolving(poop, now);
      }
    }

    updatePoopDissolving(now);

    for (const poop of grandmaPoops) {
      const dt = Math.min(100, Math.max(0, now - poop.lastFrameAt));
      poop.lastFrameAt = now;
      let remaining = dt;
      while (remaining > 0) {
        const step = Math.min(poopPhysicsSubstepMs, remaining) / 1000;
        integrateGrandmaPoop(poop, step);
        remaining -= poopPhysicsSubstepMs;
      }
      constrainPoopToViewport(poop, now);
    }

    for (let pass = 0; pass < 3; pass += 1) {
      for (let i = 0; i < grandmaPoops.length; i += 1) {
        constrainPoopToViewport(grandmaPoops[i], now);
        for (let j = i + 1; j < grandmaPoops.length; j += 1) {
          resolvePoopCollision(grandmaPoops[i], grandmaPoops[j], now);
        }
      }
    }
  }

  function integrateGrandmaPoop(poop, dt) {
    if (poop.asleep) return;
    poop.vy += poopGravity * dt;
    poop.vx *= Math.pow(poopAirDrag, dt * 60);
    poop.vy *= Math.pow(poopAirDrag, dt * 60);
    poop.angularVelocity *= Math.pow(poopAngularDrag, dt * 60);
    poop.x += poop.vx * dt;
    poop.y += poop.vy * dt;
    poop.angle += poop.angularVelocity * dt;
  }

  function constrainPoopToViewport(poop, now) {
    if (poop.beingEaten) return;

    const bounds = poopAabb(poop, now);
    if (bounds.minX < 0) {
      poop.x += -bounds.minX;
      poop.vx = Math.abs(poop.vx) * poopRestitution;
      poop.vy *= poopFriction;
      poop.angularVelocity *= -poopFriction;
    } else if (bounds.maxX > window.innerWidth) {
      poop.x -= bounds.maxX - window.innerWidth;
      poop.vx = -Math.abs(poop.vx) * poopRestitution;
      poop.vy *= poopFriction;
      poop.angularVelocity *= -poopFriction;
    }

    const updatedBounds = poopAabb(poop, now);
    if (updatedBounds.minY < 0) {
      poop.y += -updatedBounds.minY;
      poop.vy = Math.abs(poop.vy) * poopRestitution;
      poop.vx *= poopFriction;
      poop.angularVelocity *= -poopFriction;
    }

    const floorBottom = poopFloorBottom(poop, now);
    const floorOverlap = floorBottom - window.innerHeight;
    const touchingFloor = floorOverlap >= -0.5;
    if (touchingFloor) {
      if (floorOverlap > 0) poop.y -= floorOverlap;
      if (poop.vy > 0 || floorOverlap > 0) {
        poop.vy = -Math.abs(poop.vy) * poopRestitution;
        poop.vx *= poopFriction * 0.72;
        poop.angularVelocity *= poopFriction * 0.55;
      }
      if (!poop.floorContactSince) poop.floorContactSince = now;
      if (Math.abs(poop.vy) < poopSleepLinearSpeed * 1.8) poop.vy = 0;
      if (Math.abs(poop.vx) < poopSleepLinearSpeed) poop.vx = 0;
      if (Math.abs(poop.angularVelocity) < poopSleepAngularSpeed) poop.angularVelocity = 0;
      maybeSleepPoop(poop, now);
    } else {
      poop.floorContactSince = 0;
      poop.asleep = false;
    }
  }

  function poopFloorBottom(poop, now) {
    const size = poopCurrentSize(poop, now);
    const halfHeight = size * 0.42 * poopFloorFootprintScale;
    return poop.y + halfHeight;
  }

  function maybeSleepPoop(poop, now) {
    if (poop.beingEaten) return;
    if (!poop.floorContactSince || now - poop.floorContactSince < poopSleepDelayMs) return;
    const linearSpeed = Math.sqrt(poop.vx * poop.vx + poop.vy * poop.vy);
    if (linearSpeed > poopSleepLinearSpeed || Math.abs(poop.angularVelocity) > poopSleepAngularSpeed) return;
    poop.vx = 0;
    poop.vy = 0;
    poop.angularVelocity = 0;
    poop.asleep = true;
  }

  function resolvePoopCollision(first, second, now) {
    if (first.beingEaten || second.beingEaten) return false;

    const collision = poopRotatedRectCollision(first, second, now);
    if (!collision) return false;
    first.asleep = false;
    second.asleep = false;

    const correctionX = collision.normal.x * collision.depth * 0.5;
    const correctionY = collision.normal.y * collision.depth * 0.5;
    first.x -= correctionX;
    first.y -= correctionY;
    second.x += correctionX;
    second.y += correctionY;

    const relativeVelocity = {
      x: second.vx - first.vx,
      y: second.vy - first.vy,
    };
    const separatingSpeed = (relativeVelocity.x * collision.normal.x)
      + (relativeVelocity.y * collision.normal.y);
    if (separatingSpeed < 0) {
      const impulse = -(1 + poopRestitution) * separatingSpeed * 0.5;
      const impulseX = collision.normal.x * impulse;
      const impulseY = collision.normal.y * impulse;
      first.vx -= impulseX;
      first.vy -= impulseY;
      second.vx += impulseX;
      second.vy += impulseY;

      const tangent = { x: -collision.normal.y, y: collision.normal.x };
      const tangentSpeed = (relativeVelocity.x * tangent.x) + (relativeVelocity.y * tangent.y);
      const frictionImpulse = tangentSpeed * 0.18;
      first.vx += tangent.x * frictionImpulse;
      first.vy += tangent.y * frictionImpulse;
      second.vx -= tangent.x * frictionImpulse;
      second.vy -= tangent.y * frictionImpulse;

      first.angularVelocity -= tangentSpeed * 0.012;
      second.angularVelocity += tangentSpeed * 0.012;
    }

    first.vx *= 0.985;
    first.vy *= 0.985;
    second.vx *= 0.985;
    second.vy *= 0.985;
    return true;
  }

  function poopRotatedRectCollision(first, second, now) {
    const firstCorners = poopCorners(first, now);
    const secondCorners = poopCorners(second, now);
    const axes = [
      rectAxis(firstCorners[0], firstCorners[1]),
      rectAxis(firstCorners[1], firstCorners[2]),
      rectAxis(secondCorners[0], secondCorners[1]),
      rectAxis(secondCorners[1], secondCorners[2]),
    ];
    let minOverlap = Infinity;
    let bestAxis = null;

    for (const axis of axes) {
      const firstProjection = projectCorners(firstCorners, axis);
      const secondProjection = projectCorners(secondCorners, axis);
      const overlap = Math.min(firstProjection.max, secondProjection.max)
        - Math.max(firstProjection.min, secondProjection.min);
      if (overlap <= 0) return null;
      if (overlap < minOverlap) {
        minOverlap = overlap;
        bestAxis = axis;
      }
    }

    if (!bestAxis) return null;
    const betweenCenters = { x: second.x - first.x, y: second.y - first.y };
    if ((betweenCenters.x * bestAxis.x) + (betweenCenters.y * bestAxis.y) < 0) {
      bestAxis = { x: -bestAxis.x, y: -bestAxis.y };
    }
    return { normal: bestAxis, depth: minOverlap };
  }

  function poopCorners(poop, now) {
    const size = poopCurrentSize(poop, now);
    const halfWidth = size * 0.5;
    const halfHeight = size * 0.42;
    const cos = Math.cos(poop.angle);
    const sin = Math.sin(poop.angle);
    return [
      rotatePoopCorner(poop, -halfWidth, -halfHeight, cos, sin),
      rotatePoopCorner(poop, halfWidth, -halfHeight, cos, sin),
      rotatePoopCorner(poop, halfWidth, halfHeight, cos, sin),
      rotatePoopCorner(poop, -halfWidth, halfHeight, cos, sin),
    ];
  }

  function rotatePoopCorner(poop, x, y, cos, sin) {
    return {
      x: poop.x + x * cos - y * sin,
      y: poop.y + x * sin + y * cos,
    };
  }

  function rectAxis(first, second) {
    const edge = normalizeVector({
      x: second.x - first.x,
      y: second.y - first.y,
    });
    return { x: -edge.y, y: edge.x };
  }

  function projectCorners(corners, axis) {
    let min = Infinity;
    let max = -Infinity;
    for (const corner of corners) {
      const projection = corner.x * axis.x + corner.y * axis.y;
      min = Math.min(min, projection);
      max = Math.max(max, projection);
    }
    return { min, max };
  }

  function poopAabb(poop, now) {
    const corners = poopCorners(poop, now);
    return corners.reduce((bounds, corner) => ({
      minX: Math.min(bounds.minX, corner.x),
      maxX: Math.max(bounds.maxX, corner.x),
      minY: Math.min(bounds.minY, corner.y),
      maxY: Math.max(bounds.maxY, corner.y),
    }), {
      minX: Infinity,
      maxX: -Infinity,
      minY: Infinity,
      maxY: -Infinity,
    });
  }

  function poopCurrentSize(poop, now) {
    return poop.size * grandmaPoopScale(poop, now) * (poop.eatScale == null ? 1 : poop.eatScale) * (poop.dissolveScale == null ? 1 : poop.dissolveScale);
  }

  function queuePoopWormSpawn(now) {
    pendingPoopWormSpawns += 1;
    spawnPendingPoopWorms(now);
  }

  function spawnPendingPoopWorms(now) {
    if (!wormSprite || !wormSprite.ready) return;
    while (pendingPoopWormSpawns > 0) {
      if (!spawnPoopWorm(now)) return;
      pendingPoopWormSpawns -= 1;
    }
  }

  function spawnPoopWorm(now) {
    if (!wormSprite || !wormSprite.ready) return false;
    const groundY = wormGroundY();
    const scale = wormBaseScale;
    const length = wormSprite.lengthAtScale(scale);
    const direction = Math.random() < 0.5 ? -1 : 1;
    const left = wormPatrolMargin + Math.random() * Math.max(1, window.innerWidth - wormPatrolMargin * 2 - length);
     poopWorms.push({
       id: nextPoopWormId++,
       spawnedAt: now,
       x: direction >= 0 ? left : left + length,
       baselineY: wormSprite.groundBaselineY(groundY, scale),
       scale,
       direction,
       patrolDirection: direction,
       phase: Math.random() * Math.PI * 2,
       lastFrameAt: now,
       lastFailedPoop: null,
       lastFailedAt: 0,
       lastAteAt: 0,
       lastDirectionChangeAt: now,
       targetPoop: null,
       eatingPoop: null,
       eatStartedAt: 0,
       nextCrunchAt: 0,
       eatingDirection: direction,
       eatenPoops: 0,
     });
    return true;
  }

  function advancePoopWorms(now) {
  if (!wormSprite || !wormSprite.ready) return;
  spawnPendingPoopWorms(now);
  
  for (const worm of poopWorms) {
    if (worm.dissolving) continue;
    
    const dt = Math.min(100, Math.max(0, now - (worm.lastFrameAt || now))) / 1000;
    worm.lastFrameAt = now;
    worm.phase += dt * (worm.eatingPoop ? 11.5 : 8.5);

    if (worm.eatingPoop) {
      advanceWormEating(worm, now);
      anchorWormToGround(worm, now);
      continue;
    }

    anchorWormToGround(worm, now);
    
    // Skip targeting if worm recently finished eating - prevents lockup with other nearby worms
    if (worm.lastAteAt && now - worm.lastAteAt < 800) {
      patrolWorm(worm, dt, now);
      continue;
    }
    
    const targetPoop = nearestTouchablePoop(worm, now);
    if (targetPoop && claimWormPoop(worm, targetPoop, now)) {
      worm.targetPoop = targetPoop;
    } else {
      releaseWormPoopClaim(worm);
      worm.targetPoop = null;
      if (targetPoop) {
        worm.lastFailedPoop = targetPoop;
        worm.lastFailedAt = now;
        // Try to find another poop immediately instead of going to patrol
        const nextPoop = nearestTouchablePoop(worm, now);
        if (nextPoop && claimWormPoop(worm, nextPoop, now)) {
          worm.targetPoop = nextPoop;
        }
      }
    }
    
    if (!worm.targetPoop) {
      patrolWorm(worm, dt, now);
      continue;
    }

    // Get mouth position once per frame to avoid phase jitter
    const pose = wormPose(worm, now);
    const mouth = wormSprite.mouthPoint(pose);
    const target = worm.targetPoop;
    
    // Calculate distance and direction to target
    const distanceToTarget = target.x - mouth.x;
    const stopThreshold = poopCurrentSize(target, now) * 0.4 + 10 * worm.scale;
    const absoluteDistance = Math.abs(distanceToTarget);
    
    // If within eating range, try to eat
    if (absoluteDistance <= stopThreshold) {
      if (!startWormEating(worm, target, now)) {
        releaseWormPoopClaim(worm);
        worm.targetPoop = null;
      }
      continue;
    }
    
    // Set direction with hysteresis to prevent flipping
    const desiredDirection = distanceToTarget > 0 ? 1 : -1;
    const shouldChangeDirection = desiredDirection !== worm.direction
      && (Math.abs(distanceToTarget) > wormDirectionDeadZone
          || now - worm.lastDirectionChangeAt >= wormDirectionChangeCooldownMs);
    if (shouldChangeDirection) {
      worm.direction = desiredDirection;
      worm.lastDirectionChangeAt = now;
    }
    
    // Move toward target, but don't overshoot
    const maxStep = wormCrawlSpeed * worm.scale * dt;
    const step = Math.min(maxStep, absoluteDistance - stopThreshold);
    worm.x += worm.direction * step;
  }
}

  function patrolWorm(worm, dt, now) {
    worm.direction = worm.patrolDirection || worm.direction || 1;
    
    // If worm recently failed to claim a poop, move away from it
    if (worm.lastFailedPoop && now - worm.lastFailedAt < 1500) {
      const mouth = wormSprite.mouthPoint(wormPose(worm, now));
      const poop = worm.lastFailedPoop;
      const poopRadius = poopCurrentSize(poop, now) * 0.4;
      const distanceToPoop = Math.abs(mouth.x - poop.x) - poopRadius;
      
      // If still too close to the failed poop, move away from it
      if (distanceToPoop < wormCrawlSpeed * worm.scale * 2) {
        const awayFromPoop = mouth.x < poop.x ? -1 : 1;
        worm.direction = awayFromPoop;
        worm.lastDirectionChangeAt = now;
        worm.patrolDirection = awayFromPoop;
      }
    }
    
    worm.x += worm.direction * wormCrawlSpeed * worm.scale * dt * 0.62;
    const bounds = wormDrawBounds(worm, now);
    if (bounds.minX < wormPatrolMargin) {
      worm.x += wormPatrolMargin - bounds.minX;
      worm.patrolDirection = 1;
      worm.direction = 1;
      worm.lastDirectionChangeAt = now;
    } else if (bounds.maxX > window.innerWidth - wormPatrolMargin) {
      worm.x -= bounds.maxX - (window.innerWidth - wormPatrolMargin);
      worm.patrolDirection = -1;
      worm.direction = -1;
      worm.lastDirectionChangeAt = now;
    }
  }

  function nearestTouchablePoop(worm, now) {
    let best = null;
    let bestDistance = Infinity;
    const mouth = wormSprite.mouthPoint(wormPose(worm, now));
    const recentlyFailedPoop = worm.lastFailedPoop && now - worm.lastFailedAt < 500 ? worm.lastFailedPoop : null;
    for (const poop of grandmaPoops) {
      if (poop.beingEaten) continue;
      if (poop.eatScale != null && poop.eatScale <= 0.05) continue;
      if (!poopIsGroundedForWorm(poop, now)) continue;
      if (poopClaimedByOtherWorm(poop, worm, now)) continue;
      if (poop === recentlyFailedPoop) continue;
      const poopRadius = poopCurrentSize(poop, now) * 0.4;
      const verticalReach = Math.abs(wormGroundY() - poopFloorBottom(poop, now));
      if (verticalReach > wormGroundReach * worm.scale) continue;
      const distance = Math.abs(mouth.x - poop.x) - poopRadius;
      // Add small random factor to prevent all worms from choosing the exact same poop
      const adjustedDistance = distance * (0.95 + Math.random() * 0.1);
      if (adjustedDistance < bestDistance) {
        best = poop;
        bestDistance = adjustedDistance;
      }
    }
    return best;
  }

  function activePoopWormById(id) {
    return poopWorms.find((worm) => worm.id === id && !worm.dissolving) || null;
  }

  function poopClaimedByOtherWorm(poop, worm, now) {
    if (poop.claimedByWormId == null || poop.claimedByWormId === worm.id) return false;
    const owner = activePoopWormById(poop.claimedByWormId);
    if (!owner || now - (poop.claimedAt || 0) > wormPoopClaimTimeoutMs) {
      clearPoopClaim(poop);
      return false;
    }
    // Also check if the owner is already eating this poop
    if (owner.eatingPoop === poop) {
      return true;
    }
    return true;
  }

  function claimWormPoop(worm, poop, now) {
    if (!poop || poop.beingEaten || poop.dissolving || poopClaimedByOtherWorm(poop, worm, now)) return false;
    if (worm.targetPoop && worm.targetPoop !== poop) {
      releaseWormPoopClaim(worm);
    }
    
    // If already claimed by another worm, this worm MUST look elsewhere - no tiebreaker
    // This ensures only one worm targets a poop at a time
    if (poop.claimedByWormId != null && poop.claimedByWormId !== worm.id) {
      return false;
    }
    
    poop.claimedByWormId = worm.id;
    poop.claimedAt = now;
    worm.targetPoop = poop;
    return true;
  }

  function releaseWormPoopClaim(worm) {
    const poop = worm.targetPoop;
    if (poop && poop.claimedByWormId === worm.id) {
      clearPoopClaim(poop);
    }
  }

  function clearPoopClaim(poop) {
    poop.claimedByWormId = null;
    poop.claimedAt = 0;
  }

  function poopIsGroundedForWorm(poop, now) {
    const touchingFloor = poopFloorBottom(poop, now) >= window.innerHeight - 0.5;
    if (!touchingFloor) return false;
    if (poop.asleep) return true;
    if (!poop.floorContactSince) return false;

    const contactAge = now - poop.floorContactSince;
    const linearSpeed = Math.sqrt(poop.vx * poop.vx + poop.vy * poop.vy);
    return contactAge >= 180
      && poop.vy >= -poopSleepLinearSpeed * 1.8
      && linearSpeed <= wormCrawlSpeed * 0.9
      && Math.abs(poop.vx) <= wormMaxTargetHorizontalSpeed
      && Math.abs(poop.angularVelocity) <= poopSleepAngularSpeed * 5;
  }

  function startWormEating(worm, poop, now) {
    if (poop.beingEaten) return false;
    if (!poopIsGroundedForWorm(poop, now)) return false;
    if (!claimWormPoop(worm, poop, now)) return false;
    poop.beingEaten = true;
    poop.asleep = true;
    poop.vx = 0;
    poop.vy = 0;
    poop.angularVelocity = 0;
    poop.floorContactSince = now;
    worm.eatingPoop = poop;
    worm.targetPoop = poop;
    worm.eatStartedAt = now;
    worm.nextCrunchAt = 0;
    worm.eatingDirection = worm.direction;
    return true;
  }

  function advanceWormEating(worm, now) {
    const poop = worm.eatingPoop;
    if (!poop) return;
    const progress = clamp01((now - worm.eatStartedAt) / wormEatDurationMs);
    poop.eatScale = Math.max(0, 1 - progress);
    poop.eatShake = Math.sin(now / 22) * (1 - progress) * 7;
    worm.direction = worm.eatingDirection || worm.direction;
    if (now >= worm.nextCrunchAt) {
      playSound(sounds.chomp);
      worm.nextCrunchAt = now + wormCrunchIntervalMs;
    }
    if (progress < 1) return;

    const index = grandmaPoops.indexOf(poop);
    if (index >= 0) grandmaPoops.splice(index, 1);
    releaseWormPoopClaim(worm);
    worm.eatenPoops = (worm.eatenPoops || 0) + 1;
    worm.scale = Math.min(wormMaxScale, worm.scale * wormGrowthMultiplier);
    anchorWormToGround(worm, now);
    worm.eatingPoop = null;
    worm.targetPoop = null;
    worm.eatStartedAt = 0;
    worm.patrolDirection = worm.direction;
    worm.lastAteAt = now;
    
    const superGrandmas = babyGrandmaSnakes.filter(b => b.drawScale > babyGrandmaDrawScale);
    const hasSuperGrandma = superGrandmas.length > 0;
    
    // If there's a super grandma, worm eats 1 poop → spawns a fly (never becomes super grandma)
    if (hasSuperGrandma) {
      beginWormDissolving(worm, now);
      pendingWormBecomingSuperGrandma = false;
      return;
    }
    
    // No super grandma - normal behavior
    if (pendingWormBecomingSuperGrandma && worm.eatenPoops === 1) {
      if (wormBecameSuperGrandmaSnake(worm, now)) {
        return;
      }
    }
    if (worm.eatenPoops >= wormPoopsToFly) {
      if (wormBecameSuperGrandmaSnake(worm, now)) {
        return;
      }
      pendingWormBecomingSuperGrandma = false;
      beginWormDissolving(worm, now);
    }
  }

  function wormGroundY() {
    return window.innerHeight - wormGroundMargin;
  }

  function anchorWormToGround(worm, now = performance.now()) {
    worm.baselineY = wormSprite.groundBaselineY(wormGroundY(), wormRigScale);
    const bounds = wormDrawBounds(worm, now);
    if (!Number.isFinite(bounds.maxY)) return;
    worm.baselineY += wormGroundY() - bounds.maxY;
  }

  function wormDrawBounds(worm, now = performance.now()) {
    return wormSprite.poseDrawBounds(wormPose(worm, now), worm.scale);
  }

  function wormPose(worm, now = performance.now()) {
    const eatingProgress = worm.eatingPoop
      ? clamp01((now - worm.eatStartedAt) / wormEatDurationMs)
      : 0;
    const visualScale = worm.scale || wormBaseScale;
    const poseScale = wormRigScale;
    const facingOffset = worm.direction >= 0 ? 0 : wormSprite.lengthAtScale(visualScale) - wormSprite.lengthAtScale(poseScale);
    return wormSprite.buildInchwormPose({
      x: worm.x - facingOffset,
      y: worm.baselineY,
      scale: poseScale,
      direction: worm.direction,
      phase: worm.phase,
      arch: wormInchwormArch,
      contraction: wormInchwormContract,
      headShake: worm.eatingPoop ? wormHeadShakeSize * (1 - eatingProgress * 0.35) : 0,
      headShakePhase: worm.phase + now / 42,
    });
  }

  function drawPoopWorms(now) {
    if (!wormSprite || !wormSprite.ready) return;
    for (const worm of poopWorms) {
      const bounds = wormDrawBounds(worm, now);
      if (bounds.minX > window.innerWidth || bounds.maxX < 0) continue;
      if (bounds.minY > window.innerHeight || bounds.maxY < 0) continue;
      if (worm.dissolving) {
        wormSprite.draw(ctx, wormPose(worm, now), { scale: worm.scale * worm.dissolveScale });
      } else {
        wormSprite.draw(ctx, wormPose(worm, now), { scale: worm.scale });
      }
    }
  }

    function manageWormLimit(now) {
      const maxWorms = 20;
      if (poopWorms.length <= maxWorms) return;
      
      // Collect worms that are not dissolving and not currently eating
      const candidates = [];
      for (let i = 0; i < poopWorms.length; i++) {
        const worm = poopWorms[i];
        if (!worm.dissolving && !worm.eatingPoop) {
          candidates.push({ index: i, worm, spawnedAt: worm.spawnedAt || now });
        }
      }
      
      // Sort by spawnedAt (oldest first)
      candidates.sort((a, b) => a.spawnedAt - b.spawnedAt);
      
      // Remove oldest worms until under limit
      let toRemove = poopWorms.length - maxWorms;
      for (let i = 0; i < candidates.length && toRemove > 0; i++) {
        const candidate = candidates[i];
        // Release any poop claim before removal
        releaseWormPoopClaim(candidate.worm);
        poopWorms.splice(candidate.index, 1);
        // Adjust indices for subsequent removals
        for (let j = i + 1; j < candidates.length; j++) {
          if (candidates[j].index > candidate.index) {
            candidates[j].index--;
          }
        }
        toRemove--;
      }
    }

  function countAvailablePoopsForWorms(now) {
    let count = 0;
    const dummyWorm = { id: -1 };
    for (const poop of grandmaPoops) {
      if (poop.beingEaten) continue;
      if (poop.dissolving) continue;
      if (poop.eatScale != null && poop.eatScale <= 0.05) continue;
      if (!poopIsGroundedForWorm(poop, now)) continue;
      if (poopClaimedByOtherWorm(poop, dummyWorm, now)) continue;
      count++;
    }
    return count;
  }

  function maybeSpawnSuperGrandmaFromHungryWorms(now) {
    // Count only active worms (not dissolving)
    const activeWorms = poopWorms.filter(w => !w.dissolving);
    if (activeWorms.length === 0) return;
    if (!snake.dead || babyGrandmaSnakes.length > 0) return;
    
    // Cooldown to prevent rapid attempts
    if (now - lastHungrySuperGrandmaSpawn < 10000) return;
    
    const availablePoops = countAvailablePoopsForWorms(now);
    if (availablePoops > 0) return;
    
    // Limit to 1 super grandma at a time
    const superGrandmas = babyGrandmaSnakes.filter(b => b.drawScale > babyGrandmaDrawScale);
    if (superGrandmas.length > 0) return;
    
    // Spawn a super grandma at a random position
    const margin = 100;
    const x = margin + Math.random() * (window.innerWidth - margin * 2);
    const y = margin + Math.random() * (window.innerHeight - margin * 2);
    const direction = { x: Math.random() - 0.5, y: Math.random() - 0.5 };
    if (spawnSuperGrandmaSnake({ x, y }, direction, now)) {
      lastHungrySuperGrandmaSpawn = now;
      pendingWormBecomingSuperGrandma = false;
    }
  }

  function updateGrandmaSnakePresence(now) {
    const grandmaCount = (snake.dead ? 0 : 1) + babyGrandmaSnakes.length;
    if (grandmaCount === 0) {
      if (lastGrandmaSnakeGoneAt === 0) {
        lastGrandmaSnakeGoneAt = now;
      }
    } else {
      lastGrandmaSnakeGoneAt = 0;
    }
  }

  function maybeSpawnSuperSnakesDueToTimeout(now) {
    if (lastGrandmaSnakeGoneAt === 0) return;
    if (now - lastGrandmaSnakeGoneAt < superSnakeSpawnTimeoutMs) return;
    
    // Spawn 2 super snakes, respecting limit of 2 super grandmas total
    const margin = 100;
    const superGrandmas = babyGrandmaSnakes.filter(b => b.drawScale > babyGrandmaDrawScale);
    const needed = 2 - superGrandmas.length;
    if (needed <= 0) return;
    
    for (let i = 0; i < needed; i++) {
      const x = margin + Math.random() * (window.innerWidth - margin * 2);
      const y = margin + Math.random() * (window.innerHeight - margin * 2);
      const direction = { x: Math.random() - 0.5, y: Math.random() - 0.5 };
      spawnSuperGrandmaSnake({ x, y }, direction, now);
    }
    lastGrandmaSnakeGoneAt = 0; // Reset to avoid repeated spawning
  }

  function beginWormDissolving(worm, now) {
    if (worm.dissolving) return;
    releaseWormPoopClaim(worm);
    worm.dissolving = true;
    worm.dissolveStartedAt = now;
    worm.dissolveProgress = 0;
    worm.dissolveScale = 1;
    worm.eatingPoop = null;
    worm.targetPoop = null;
  }

  function updateWormDissolving(now) {
    for (let i = poopWorms.length - 1; i >= 0; i--) {
      const worm = poopWorms[i];
      if (!worm.dissolving) continue;
      worm.dissolveProgress = Math.min(1, (now - worm.dissolveStartedAt) / wormDissolveDurationMs);
      worm.dissolveScale = 1 - worm.dissolveProgress;
      if (worm.dissolveProgress >= 1) {
        if (spawnFlyAtWormLocation(worm, now)) {
          poopWorms.splice(i, 1);
        }
      }
    }
  }

  function beginPoopDissolving(poop, now) {
    if (poop.dissolving) return;
    clearPoopClaim(poop);
    poop.dissolving = true;
    poop.dissolveStartedAt = now;
    poop.dissolveProgress = 0;
    poop.dissolveScale = 1;
  }

  function updatePoopDissolving(now) {
    for (let i = grandmaPoops.length - 1; i >= 0; i--) {
      const poop = grandmaPoops[i];
      if (!poop.dissolving) continue;
      poop.dissolveProgress = Math.min(1, (now - poop.dissolveStartedAt) / poopDissolveDurationMs);
      poop.dissolveScale = 1 - poop.dissolveProgress;
      if (poop.dissolveProgress >= 1) {
        grandmaPoops.splice(i, 1);
      }
    }
  }

  function spawnFlyAtWormLocation(worm, now) {
    if (!flySprite || !flySprite.ready || !flyManifest) return false;
    if (flies.length >= flyMaxCount) return false;
    const x = worm.x || window.innerWidth / 2;
    const y = (worm.baselineY || window.innerHeight - 50) - 30;
    flies.push({
      x,
      y,
      scale: flyStartScale,
      targetX: x,
      targetY: y,
      state: "flying",
      flyState: "flying",
      lastFrameAt: now,
      spawnedAt: now,
      zapCooldownUntil: now + flyZapMinCooldownMs + Math.random() * (flyZapMaxCooldownMs - flyZapMinCooldownMs),
      direction: { x: 1, y: 0 },
      rotation: 0,
      vx: 0,
      vy: 0,
      landedAt: 0,
      frameIndex: 0,
      frameTime: 0,
      growProgress: 0,
    });
    return true;
  }

  function advanceFlies(now) {
    if (!flySprite || !flySprite.ready) return;
    updateWormDissolving(now);
    const hasFlyingFlies = flies.some((f) => f.state === "flying");
    if (hasFlyingFlies && !flySoundActive) {
      playSound(sounds.fly, true);
      flySoundActive = Boolean(sounds.fly);
    } else if (!hasFlyingFlies && flySoundActive) {
      stopSound(sounds.fly);
      flySoundActive = false;
    }
    for (const fly of flies) {
      const dt = Math.min(100, Math.max(0, now - (fly.lastFrameAt || now))) / 1000;
      fly.lastFrameAt = now;
      fly.frameTime += dt * 1000;
      if (fly.frameTime >= 120) {
        fly.frameTime = 0;
        fly.frameIndex = (fly.frameIndex + 1) % (flyManifest.frameCount || 6);
      }
      if (fly.growProgress < 1) {
        fly.growProgress = Math.min(1, (now - fly.spawnedAt || now) / flyGrowDurationMs);
        const eased = 1 - Math.pow(1 - fly.growProgress, 3);
        fly.scale = flyStartScale + (flySpriteScale - flyStartScale) * eased;
      }
      if (fly.state !== "falling" && fly.state !== "fallen" && now - fly.spawnedAt >= flyLifetimeMs) {
        beginFlyFalling(fly, now);
      }
      if (fly.state === "falling") {
        advanceFallingFly(fly, dt, now);
        continue;
      }
      if (fly.state === "fallen") {
        continue;
      }
      if (fly.state === "flying") {
        const dx = fly.targetX - fly.x;
        const dy = fly.targetY - fly.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 5) {
          fly.state = "landing";
          fly.waitUntil = now + flyMinPauseMs + Math.random() * (flyMaxPauseMs - flyMinPauseMs);
        } else {
          const speed = flySpeed * dt;
          const move = Math.min(speed, distance);
          fly.x += (dx / distance) * move;
          fly.y += (dy / distance) * move;
          fly.direction = normalizeVector({ x: dx, y: dy });
        }
      } else if (fly.state === "landing") {
        if (now >= fly.waitUntil) {
          fly.state = "flying";
          fly.targetX = flyPatrolMargin + Math.random() * Math.max(1, window.innerWidth - flyPatrolMargin * 2);
          fly.targetY = 50 + Math.random() * (window.innerHeight - 150);
        }
      }
      maybeFlyZap(fly, now);
    }
    pruneFlyZaps(now);
    for (let i = flies.length - 1; i >= 0; i--) {
      const fly = flies[i];
      if (fly.state === "fallen" && now - fly.landedAt >= flyCorpseDeleteMs) {
        flies.splice(i, 1);
      }
    }
  }

  function beginFlyFalling(fly, now) {
    fly.state = "falling";
    fly.flyState = "falling";
    fly.vx = (Math.random() - 0.5) * 90;
    fly.vy = -70 - Math.random() * 45;
    fly.rotation = 0;
    fly.landedAt = 0;
  }

  function advanceFallingFly(fly, dt, now) {
    fly.vy += 980 * dt;
    fly.x += fly.vx * dt;
    fly.y += fly.vy * dt;
    fly.rotation += (fly.vx >= 0 ? 1 : -1) * dt * 6;
    const floorY = window.innerHeight - Math.max(10, (flyManifest.height * fly.scale) / 2);
    if (fly.y >= floorY) {
      fly.y = floorY;
      fly.vx = 0;
      fly.vy = 0;
      fly.rotation = Math.PI / 2;
      fly.state = "fallen";
      fly.flyState = "fallen";
      fly.landedAt = now;
    }
  }

  function maybeFlyZap(fly, now) {
    if (now < (fly.zapCooldownUntil || 0)) return;
    const target = nearestGrandmaTarget({ x: fly.x, y: fly.y });
    if (!target || target.distance > flyZapRange) {
      fly.zapCooldownUntil = now + 250;
      return;
    }
    const direction = normalizeVector({ x: target.head.x - fly.x, y: target.head.y - fly.y });
    fly.direction = direction;
    const color = flyZapColors[Math.floor(Math.random() * flyZapColors.length)];
    const start = {
      x: fly.x + direction.x * Math.max(10, flyManifest.width * fly.scale * 0.32),
      y: fly.y + direction.y * Math.max(10, flyManifest.height * fly.scale * 0.2),
    };
    const end = {
      x: target.head.x,
      y: target.head.y,
    };
    flyZaps.push({ start, end, color, createdAt: now, duration: flyZapDurationMs });
    damageGrandmaSnake(target.grandma, flyZapDamage, now);
    playSound(sounds.flyZap);
    fly.zapCooldownUntil = now + flyZapMinCooldownMs + Math.random() * (flyZapMaxCooldownMs - flyZapMinCooldownMs);
  }

  function nearestGrandmaTarget(point) {
    let best = null;
    const consider = (grandma, drawScale) => {
      if (!grandma || grandma.dead || !grandma.heatSegments || grandma.heatSegments.length === 0) return;
      const head = grandma.heatSegments[0];
      const distance = pixelDistance(point, head);
      if (!best || distance < best.distance) {
        best = { grandma, head, distance, drawScale };
      }
    };
    consider(snake, 1);
    for (const baby of babyGrandmaSnakes) {
      consider(baby, baby.drawScale || babyGrandmaDrawScale);
    }
    return best;
  }

  function damageGrandmaSnake(grandma, damage, now) {
    if (!grandma || grandma.dead) return;
    grandma.maxHp = grandma.maxHp || grandmaMaxHp;
    grandma.hp = Math.max(0, (Number.isFinite(grandma.hp) ? grandma.hp : grandma.maxHp) - damage);
    if (grandma.hp > 0) return;
    killGrandmaSnake(grandma, now);
  }

  function killGrandmaSnake(grandma, now) {
    if (grandma.dead) return;
    grandma.enraged = true;
    grandma.enrageStart = now;
    grandma.enrageEndedAt = now;
    grandma.dead = true;
    grandma.heatSegments = [];
    if (grandma === snake) {
      snake.segments = [];
      snake.previousSegments = [];
      snake.enrageEatenCount = 0;
      addCombatLogLine("grandma", "ENRAGED! Grandma deleted.", now, "shout");
      return;
    }
    const index = babyGrandmaSnakes.indexOf(grandma);
    if (index >= 0) babyGrandmaSnakes.splice(index, 1);
    addCombatLogLine("grandma", "A Grandma snake enrages and disappears.", now, "shout");
  }

  function pruneFlyZaps(now) {
    for (let i = flyZaps.length - 1; i >= 0; i--) {
      const zap = flyZaps[i];
      if (now - zap.createdAt >= zap.duration) {
        flyZaps.splice(i, 1);
      }
    }
  }

  function drawFlies(now) {
    if (!flySprite || !flySprite.ready || !flyManifest) return;
    const frameWidth = flyManifest.width;
    const frameHeight = flyManifest.height;
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    drawFlyZaps(now);
    for (const fly of flies) {
      ctx.save();
      ctx.translate(fly.x, fly.y);
      ctx.rotate(fly.rotation || 0);
      ctx.scale(fly.scale, fly.scale);
      ctx.drawImage(
        flySprite,
        fly.frameIndex * frameWidth,
        0,
        frameWidth,
        frameHeight,
        -frameWidth / 2,
        -frameHeight / 2,
        frameWidth,
        frameHeight
      );
      ctx.restore();
    }
    ctx.restore();
  }

  function drawFlyZaps(now) {
    for (const zap of flyZaps) {
      const progress = clamp01((now - zap.createdAt) / zap.duration);
      const alpha = 1 - progress;
      const jitter = 2 + progress * 5;
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.lineCap = "round";
      ctx.shadowColor = zap.color.beam;
      ctx.shadowBlur = 16;
      ctx.strokeStyle = zap.color.beam;
      ctx.lineWidth = 7;
      drawJaggedZapLine(zap.start, zap.end, jitter);
      ctx.strokeStyle = zap.color.core;
      ctx.lineWidth = 2.5;
      drawJaggedZapLine(zap.start, zap.end, jitter * 0.55);
      ctx.fillStyle = zap.color.ball;
      ctx.beginPath();
      ctx.arc(zap.end.x, zap.end.y, 8 + (1 - alpha) * 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = zap.color.core;
      ctx.beginPath();
      ctx.arc(zap.end.x, zap.end.y, 3.5 + (1 - alpha) * 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  function drawJaggedZapLine(start, end, jitter) {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const normal = distance > 0.001 ? { x: -dy / distance, y: dx / distance } : { x: 0, y: 1 };
    const segments = 4;
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    for (let i = 1; i < segments; i += 1) {
      const t = i / segments;
      const offset = (Math.random() - 0.5) * jitter;
      ctx.lineTo(start.x + dx * t + normal.x * offset, start.y + dy * t + normal.y * offset);
    }
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
  }

  function grandmaPoopScale(poop, now) {
    const progress = clamp01((now - poop.createdAt) / poopGrowDurationMs);
    const eased = 1 - ((1 - progress) * (1 - progress));
    return poopStartScale + (1 - poopStartScale) * eased;
  }

  function drawGrandmaPoops(now) {
    if (!poopSprite.complete || !poopSprite.naturalWidth || !poopSprite.naturalHeight) return;
    const frameWidth = poopSprite.naturalWidth / poopFrameCount;
    const frameHeight = poopSprite.naturalHeight;
    const frame = Math.floor((now / poopAnimationFrameMs) % poopFrameCount);

    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    for (const poop of grandmaPoops) {
      const size = poopCurrentSize(poop, now);
      const shake = poop.eatShake || 0;
      ctx.save();
      ctx.translate(poop.x + shake, poop.y - Math.abs(shake) * 0.25);
      ctx.rotate(poop.angle);
      ctx.drawImage(
        poopSprite,
        frame * frameWidth,
        0,
        frameWidth,
        frameHeight,
        -size / 2,
        -size / 2,
        size,
        size,
      );
      ctx.restore();
    }
    ctx.restore();
  }

  function drawSnake(now) {
    if (!config.snakeEnabled) return;
    if (!grandmaHeadSprite.complete || !grandmaHeadSprite.naturalWidth || !grandmaHeadSprite.naturalHeight) return;
    if (snake.dead && babyGrandmaSnakes.length === 0) return;
    if (snake.mode === "heat") {
      drawHeatSeekingSnake(now);
      return;
    }
    if (snake.dead) return;
    
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
    for (const baby of babyGrandmaSnakes) {
      if (baby.dead) continue;
      drawHeatSnakeSegments(baby.heatSegments, now, baby.drawScale || babyGrandmaDrawScale);
    }
    if (!snake.dead) {
      drawHeatSnakeSegments(snake.heatSegments, now, 1);
    }
  }

  function drawHeatSnakeSegments(segments, now, drawScale) {
    const sizes = segmentSizeMultipliers(segments.length);
    for (let i = segments.length - 1; i >= 0; i -= 1) {
      const segment = segments[i];
      const isHead = i === 0;
      const baseSize = isHead ? snakeHeadDrawSize : snakeBodyDrawSize;
      const size = baseSize * sizes[i] * enrageSizeMultiplier(now) * drawScale;
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

  function heatSegmentSpacing(firstIndex, secondIndex, sizes) {
    const firstBaseSize = firstIndex === 0 ? snakeHeadDrawSize : snakeBodyDrawSize;
    const secondBaseSize = secondIndex === 0 ? snakeHeadDrawSize : snakeBodyDrawSize;
    const firstRadius = (firstBaseSize * sizes[firstIndex]) / 2;
    const secondRadius = (secondBaseSize * sizes[secondIndex]) / 2;
    return Math.max(4, firstRadius + secondRadius - heatSegmentVisualGap);
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

  function updateFakeCursor(now) {
    if (!fakeCursor.initialized) {
      fakeCursor.x = window.innerWidth * 0.5;
      fakeCursor.y = window.innerHeight * 0.5;
      fakeCursor.initialized = true;
      fakeCursor.waitUntil = now + randomFakeCursorPauseMs();
      return;
    }

    if (now < fakeCursor.waitUntil) return;
    if (!fakeCursor.path) {
      fakeCursor.path = buildFakeCursorPath(now);
      return;
    }

    const progress = Math.max(0, Math.min(1, (now - fakeCursor.path.startedAt) / fakeCursor.path.durationMs));
    const eased = easeInOutSine(progress);
    const point = sampleCubicBezier(
      fakeCursor.path.start,
      fakeCursor.path.controlA,
      fakeCursor.path.controlB,
      fakeCursor.path.end,
      eased
    );
    fakeCursor.x = point.x;
    fakeCursor.y = point.y;
    if (progress >= 1) {
      fakeCursor.x = fakeCursor.path.end.x;
      fakeCursor.y = fakeCursor.path.end.y;
      fakeCursor.path = null;
      fakeCursor.waitUntil = now + randomFakeCursorPauseMs();
    }
  }

  function buildFakeCursorPath(now) {
    const start = { x: fakeCursor.x, y: fakeCursor.y };
    const end = chooseFakeCursorWaypoint();
    const distance = Math.max(1, pixelDistance(start, end));
    const durationMs = Math.max(
      fakeCursorMinPathMs,
      Math.min(fakeCursorMaxPathMs, (distance / fakeCursorSpeed) * 1000 * (1.35 + Math.random() * 0.8))
    );
    const midpoint = {
      x: (start.x + end.x) / 2,
      y: (start.y + end.y) / 2,
    };
    const angle = Math.atan2(end.y - start.y, end.x - start.x);
    const normal = {
      x: -Math.sin(angle),
      y: Math.cos(angle),
    };
    const curveStrength = Math.min(Math.max(distance * (0.22 + Math.random() * 0.38), 80), 360);
    const curveSign = Math.random() < 0.5 ? -1 : 1;
    const randomA = randomScreenPoint(0.08, 0.92);
    const randomB = randomScreenPoint(0.08, 0.92);
    return {
      start,
      controlA: clampScreenPoint({
        x: start.x + (midpoint.x - start.x) * 0.55 + normal.x * curveStrength * curveSign + (randomA.x - midpoint.x) * 0.22,
        y: start.y + (midpoint.y - start.y) * 0.55 + normal.y * curveStrength * curveSign + (randomA.y - midpoint.y) * 0.22,
      }),
      controlB: clampScreenPoint({
        x: end.x + (midpoint.x - end.x) * 0.55 - normal.x * curveStrength * curveSign + (randomB.x - midpoint.x) * 0.22,
        y: end.y + (midpoint.y - end.y) * 0.55 - normal.y * curveStrength * curveSign + (randomB.y - midpoint.y) * 0.22,
      }),
      end,
      startedAt: now,
      durationMs,
    };
  }

  function chooseFakeCursorWaypoint() {
    if (bidenWaypointBuffer.length > 0 && Math.random() < 0.72) {
      const waypoint = bidenWaypointBuffer[Math.floor(Math.random() * bidenWaypointBuffer.length)];
      return {
        x: waypoint.normX * window.innerWidth,
        y: waypoint.normY * window.innerHeight,
      };
    }
    return randomScreenPoint(0.12, 0.88);
  }

  function randomScreenPoint(min, max) {
    return {
      x: window.innerWidth * (min + Math.random() * (max - min)),
      y: window.innerHeight * (min + Math.random() * (max - min)),
    };
  }

  function clampScreenPoint(point) {
    const margin = fakeCursorDrawSize / 2;
    return {
      x: Math.max(margin, Math.min(window.innerWidth - margin, point.x)),
      y: Math.max(margin, Math.min(window.innerHeight - margin, point.y)),
    };
  }

  function sampleCubicBezier(start, controlA, controlB, end, t) {
    const inv = 1 - t;
    const inv2 = inv * inv;
    const t2 = t * t;
    return {
      x: inv2 * inv * start.x + 3 * inv2 * t * controlA.x + 3 * inv * t2 * controlB.x + t2 * t * end.x,
      y: inv2 * inv * start.y + 3 * inv2 * t * controlA.y + 3 * inv * t2 * controlB.y + t2 * t * end.y,
    };
  }

  function easeInOutSine(t) {
    return -(Math.cos(Math.PI * t) - 1) / 2;
  }

  function randomFakeCursorPauseMs() {
    return fakeCursorMinPauseMs + Math.random() * (fakeCursorMaxPauseMs - fakeCursorMinPauseMs);
  }

  function drawFakeCursor(now) {
    updateFakeCursor(now);
    if (!fakeCursor.initialized) return;

    ctx.save();
    ctx.translate(fakeCursor.x, fakeCursor.y);
    ctx.rotate(Math.sin(now / 900) * 0.045);
    ctx.shadowColor = "rgba(63, 199, 235, 0.85)";
    ctx.shadowBlur = 16;
    ctx.imageSmoothingEnabled = false;
    if (fakeCursorSprite.complete && fakeCursorSprite.naturalWidth && fakeCursorSprite.naturalHeight) {
      ctx.drawImage(fakeCursorSprite, -fakeCursorDrawSize / 2, -fakeCursorDrawSize / 2, fakeCursorDrawSize, fakeCursorDrawSize);
    } else {
      drawFakeCursorFallback();
    }
    ctx.restore();
  }

  function drawFakeCursorFallback() {
    const size = fakeCursorDrawSize;
    ctx.fillStyle = "rgba(63, 199, 235, 0.92)";
    ctx.strokeStyle = "rgba(0, 0, 0, 0.85)";
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(-size * 0.28, -size * 0.42);
    ctx.lineTo(size * 0.28, 0);
    ctx.lineTo(size * 0.02, size * 0.07);
    ctx.lineTo(size * 0.2, size * 0.42);
    ctx.lineTo(size * 0.02, size * 0.5);
    ctx.lineTo(-size * 0.16, size * 0.14);
    ctx.lineTo(-size * 0.38, size * 0.32);
    ctx.closePath();
    ctx.stroke();
    ctx.fill();
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

  function updateHudMessages(now) {
    for (const message of hudMessages) {
      if (message.repeatIntervalMs <= 0) continue;
      if (now < message.nextRepeatAt) continue;
      message.displayedAt = now;
      message.expiresAt = now + message.ttlMs;
      message.nextRepeatAt = now + message.repeatIntervalMs;
    }
    for (let i = hudMessages.length - 1; i >= 0; i -= 1) {
      const message = hudMessages[i];
      if (message.repeatIntervalMs > 0) continue;
      if (now >= message.expiresAt) {
        hudMessages.splice(i, 1);
      }
    }
  }

  function drawHudMessages(now) {
    updateHudMessages(now);
    const visibleMessages = hudMessages.filter((message) => now < message.expiresAt);
    if (!visibleMessages.length) return;

    const columnWidth = Math.max(280, window.innerWidth / 3);
    const x = (window.innerWidth - columnWidth) / 2;
    const topMargin = window.innerHeight * 0.05;
    const paddingX = 18;
    const paddingY = 12;
    const gap = 12;
    const radius = 14;
    const fontSize = Math.max(18, Math.min(30, window.innerWidth / 52));
    const lineHeight = Math.round(fontSize * 1.28);
    const maxTextWidth = columnWidth - paddingX * 2;
    let y = topMargin;

    ctx.save();
    ctx.font = `800 ${fontSize}px Georgia, "Times New Roman", serif`;
    ctx.textBaseline = "top";
    ctx.shadowColor = "rgba(0, 0, 0, 0.98)";
    ctx.shadowBlur = 5;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;

    for (const message of visibleMessages.slice(-8)) {
      const lines = layoutPlainTextLines(message.text, maxTextWidth);
      const cardHeight = paddingY * 2 + lines.length * lineHeight;
      if (y + cardHeight > window.innerHeight - 12) break;
      const age = Math.max(0, now - message.displayedAt);
      const remaining = Math.max(0, message.expiresAt - now);
      const fadeIn = Math.min(1, age / 250);
      const fadeOut = Math.min(1, remaining / 600);
      const alpha = Math.max(0, Math.min(1, fadeIn, fadeOut));

      ctx.shadowColor = "transparent";
      ctx.fillStyle = `rgba(12, 8, 2, ${0.64 * alpha})`;
      ctx.strokeStyle = `rgba(214, 173, 82, ${0.42 * alpha})`;
      ctx.lineWidth = 1.5;
      drawRoundedRect(x, y, columnWidth, cardHeight, radius);
      ctx.fill();
      ctx.stroke();

      ctx.shadowColor = "rgba(0, 0, 0, 0.98)";
      ctx.fillStyle = `rgba(255, 215, 84, ${alpha})`;
      let lineY = y + paddingY;
      for (const line of lines) {
        ctx.fillText(line, x + paddingX, lineY, maxTextWidth);
        lineY += lineHeight;
      }
      y += cardHeight + gap;
    }
    ctx.restore();
  }

  function drawBidenTimer(now) {
    const width = Math.max(250, Math.min(360, window.innerWidth * 0.22));
    const height = 58;
    const x = 24;
    const y = 24;
    const radius = 14;
    const paddingX = 16;
    const baselineY = y + 18;
    const labelFont = "800 21px Verdana, Geneva, sans-serif";
    const timeFont = "800 24px Verdana, Geneva, sans-serif";
    const label = "Biden";
    const suffix = " Time:";
    const labelColor = "rgba(170, 211, 114, 0.98)";
    const white = "rgba(255, 255, 255, 0.98)";

    ctx.save();
    ctx.fillStyle = "rgba(8, 10, 14, 0.66)";
    ctx.strokeStyle = "rgba(70, 156, 255, 0.34)";
    ctx.lineWidth = 1.5;
    drawRoundedRect(x, y, width, height, radius);
    ctx.fill();
    ctx.stroke();

    ctx.textBaseline = "top";
    ctx.shadowColor = "rgba(0, 0, 0, 0.98)";
    ctx.shadowBlur = 5;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;

    ctx.font = labelFont;
    ctx.fillStyle = labelColor;
    ctx.fillText(label, x + paddingX, baselineY);
    const labelWidth = ctx.measureText(label).width;
    ctx.fillStyle = labelColor;
    ctx.fillText(suffix, x + paddingX + labelWidth, baselineY);
    const suffixWidth = ctx.measureText(suffix).width;

    ctx.font = timeFont;
    const timeText = bidenTimerText(now);
    const timeWidth = ctx.measureText(timeText).width;
    const nearTimeX = x + paddingX + labelWidth + suffixWidth + 18;
    const rightTimeX = x + width - paddingX - timeWidth;
    const timeX = Math.min(rightTimeX, nearTimeX + (rightTimeX - nearTimeX) * 0.5);
    ctx.fillStyle = white;
    ctx.fillText(timeText, timeX, y + 16);
    ctx.restore();
  }

  function bidenTimerText(now) {
    if (!bidenTimer.available || bidenTimer.remainingSeconds == null) return "--:--";
    const elapsed = Math.max(0, (now - bidenTimer.receivedAt) / 1000);
    const remaining = Math.max(0, bidenTimer.remainingSeconds - elapsed);
    const minutes = Math.floor(remaining / 60);
    const seconds = Math.floor(remaining % 60);
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  function layoutPlainTextLines(text, maxWidth) {
    const lines = [];
    const words = String(text || "").split(/\s+/).filter(Boolean);
    let current = "";
    for (const word of words) {
      const candidate = current ? `${current} ${word}` : word;
      if (!current && ctx.measureText(candidate).width > maxWidth) {
        lines.push(...splitLongWord(candidate, maxWidth));
        current = "";
        continue;
      }
      if (ctx.measureText(candidate).width <= maxWidth || !current) {
        current = candidate;
        continue;
      }
      lines.push(current);
      current = word;
    }
    if (current) lines.push(current);
    return lines.length ? lines : [""];
  }

  function drawRoundedRect(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
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
    const color = wowClassColors[String(speaker).toLowerCase()] || wowClassColors.grandma;
    return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
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
    maybeAddGmGithubQuip(now);
    if (!config.logOnly) {
      maybeAddDurgularYell(now);
      maybeAddTwitchChatQuip(now);
      advanceSnake(now);
      drawSnake(now);
      drawGrandmaPoops(now);
      drawPoopWorms(now);
      drawFlies(now);
      drawFakeCursor(now);
      drawBidens(now);
      const anyGrandmaAlive = !snake.dead || babyGrandmaSnakes.some(b => !b.dead);
      if (anyGrandmaAlive) {
        drawEnrageMeter(now);
      }
      drawBidenTimer(now);
      drawHudMessages(now);
    }
    drawCombatLog(now);
    animationFrameId = requestAnimationFrame(draw);
  }

   function cleanup() {
     if (animationFrameId !== null) {
       cancelAnimationFrame(animationFrameId);
       animationFrameId = null;
     }
     window.removeEventListener("resize", handleResize);
     if (events) events.close();
     
     // Remove audio elements from DOM
     for (const key in sounds) {
       const pool = sounds[key];
       if (pool && pool.clips) {
         for (const audio of pool.clips) {
           if (audio.parentNode) {
             audio.parentNode.removeChild(audio);
           }
         }
       }
     }
   }
   
   // Attach cleanup to page unload
   window.addEventListener("beforeunload", cleanup);
   window.addEventListener("pagehide", cleanup);
   
   resizeCanvas();
   resetSnake();
   const handleResize = () => resizeCanvas();
   window.addEventListener("resize", handleResize);
  wormSprite = new AsepriteBoneSprite("", {
    manifestUrl: "/assets/generated/sprites/worm_with_bones.layers.json",
    imageLayerName: "worm",
    bonesLayerName: "bones",
    sliceCount: 64,
  });
  wormSprite.load().catch((error) => {
    console.warn("Worm bone sprite failed to load.", error);
    wormSprite = null;
  });

  fetch("/assets/generated/sprites/fly_flying.json")
    .then((res) => res.json())
    .then((manifest) => {
      flyManifest = manifest;
      flySprite = new Image();
      flySprite.src = manifest.spritesheet;
      flySprite.onload = () => {
        flySprite.ready = true;
      };
    })
    .catch((error) => {
      console.warn("Fly sprite manifest failed to load.", error);
    });

   events = new EventSource("/events");
  events.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "hud_message") {
        addHudMessage(payload, performance.now());
        return;
      }
      if (payload.type === "hud_message_delete") {
        deleteHudMessage(payload);
        return;
      }
      if (payload.type === "biden_timer") {
        updateBidenTimer(payload, performance.now());
        return;
      }
      if (payload.type === "combat_log") {
        addCombatLogLine(payload.speaker || "gm", payload.text || "", performance.now(), payload.channel || "say");
        return;
      }
      addSpawn(payload);
    } catch (_error) {
      // Ignore malformed overlay events.
    }
  };

   animationFrameId = requestAnimationFrame(draw);
})();
