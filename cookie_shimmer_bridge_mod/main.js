Game.registerMod("shimmer bridge", {
	init: function () {
		let lastPayload = "";
		let lastNonEmptyPayload = "";
		let lastWrite = 0;
		let cachedStore = null;
		let cachedBank = null;
		let cachedGarden = null;
		let cachedSpellbook = null;
		let cachedBuildings = null;
		let cachedUpgrades = null;
		let cachedBestUpgrade = null;
		let cacheTimestamp = 0;
		let lastGoldenDecision = null;
		let goldenDecisionLog = [];
		let blockedGoldenDecisions = 0;
		const WRITE_INTERVAL_MS = 150;
		const STALE_WRITE_MS = 500;
		const HEAVY_SECTION_CACHE_MS = 500;
		const GOLDEN_DECISION_LOG_LIMIT = 25;
		const WRATH_GATE_ENABLED = true;
		const BLOCKED_WRATH_CHOICES = new Set(["clot", "ruin cookies", "cursed finger"]);
		const RISKY_WRATH_CHOICES = new Set(["building special"]);

		const pointInRect = (x, y, rect) => {
			if (!rect) return false;
			return (
				typeof rect.left === "number" &&
				typeof rect.top === "number" &&
				typeof rect.right === "number" &&
				typeof rect.bottom === "number" &&
				x >= rect.left &&
				x < rect.right &&
				y >= rect.top &&
				y < rect.bottom
			);
		};

		const chooseSafePointInRect = (rect, avoidRects) => {
			if (!rect) return null;
			const left = rect.left;
			const top = rect.top;
			const right = rect.right;
			const bottom = rect.bottom;
			if (
				typeof left !== "number" ||
				typeof top !== "number" ||
				typeof right !== "number" ||
				typeof bottom !== "number" ||
				right <= left ||
				bottom <= top
			) {
				return null;
			}
			const inset = 2;
			const minX = left + inset;
			const maxX = right - inset;
			const minY = top + inset;
			const maxY = bottom - inset;
			const candidateXs = [
				Math.round((left + right) / 2),
				Math.round(left + (right - left) * 0.3),
				Math.round(left + (right - left) * 0.7),
			];
			const candidateYs = [
				maxY,
				Math.round(bottom - 4),
				Math.round(bottom - 6),
				minY,
				Math.round(top + 4),
				Math.round((top + bottom) / 2),
			];
			for (let yi = 0; yi < candidateYs.length; yi++) {
				const y = Math.max(minY, Math.min(maxY, candidateYs[yi]));
				for (let xi = 0; xi < candidateXs.length; xi++) {
					const x = Math.max(minX, Math.min(maxX, candidateXs[xi]));
					let blocked = false;
					for (let i = 0; i < avoidRects.length; i++) {
						if (pointInRect(x, y, avoidRects[i])) {
							blocked = true;
							break;
						}
					}
					if (!blocked) return [x, y];
				}
			}
			return null;
		};

		const getRect = (el, options) => {
			if (!el || !el.getBoundingClientRect) return null;
			const rect = el.getBoundingClientRect();
			if (!rect || !isFinite(rect.left) || !isFinite(rect.top) || rect.width <= 0 || rect.height <= 0) {
				return null;
			}
			const avoidRects = Array.isArray(options && options.avoidRects)
				? options.avoidRects.filter(Boolean)
				: [];
			const rawCenterX = Math.round((rect.left + rect.right) / 2);
			const rawCenterY = Math.round((rect.top + rect.bottom) / 2);
			let clickX = rawCenterX;
			let clickY = rawCenterY;
			if (avoidRects.length > 0) {
				const safePoint = chooseSafePointInRect(
					{
						left: Math.round(rect.left),
						top: Math.round(rect.top),
						right: Math.round(rect.right),
						bottom: Math.round(rect.bottom),
					},
					avoidRects
				);
				if (safePoint) {
					clickX = Math.round(safePoint[0]);
					clickY = Math.round(safePoint[1]);
				}
			}
			return {
				left: Math.round(rect.left),
				top: Math.round(rect.top),
				right: Math.round(rect.right),
				bottom: Math.round(rect.bottom),
				width: Math.round(rect.width),
				height: Math.round(rect.height),
				centerX: clickX,
				centerY: clickY,
				clickX: clickX,
				clickY: clickY,
				rawCenterX: rawCenterX,
				rawCenterY: rawCenterY,
			};
		};

		const isElementEnabled = (el) => {
			if (!el) return false;
			if (el.disabled) return false;
			if (el.classList) {
				if (el.classList.contains("disabled")) return false;
				if (el.classList.contains("bankButtonOff")) return false;
			}
			const className =
				typeof el.className === "string"
					? el.className
					: el.className && typeof el.className.baseVal === "string"
						? el.className.baseVal
						: "";
			if (className.indexOf("disabled") !== -1) return false;
			if (className.indexOf("bankButtonOff") !== -1) return false;
			if (el.getAttribute && el.getAttribute("aria-disabled") === "true") return false;
			return true;
		};

		const findFirstElement = (selectors) => {
			for (let i = 0; i < selectors.length; i++) {
				try {
					const el = document.querySelector(selectors[i]);
					if (el) return el;
				} catch (err) {}
			}
			return null;
		};

		const findFirstElementByText = (selectors, pattern) => {
			for (let i = 0; i < selectors.length; i++) {
				let nodes = [];
				try {
					nodes = document.querySelectorAll(selectors[i]);
				} catch (err) {
					nodes = [];
				}
				for (let j = 0; j < nodes.length; j++) {
					const node = nodes[j];
					const text = (node && node.textContent ? node.textContent : "").trim();
					if (text && pattern.test(text)) return node;
				}
			}
			return null;
		};

		const getRectBySelectors = (selectors) => {
			return getRect(findFirstElement(selectors));
		};

		const rectIntersects = (a, b) => {
			if (!a || !b) return false;
			return !(
				a.right <= b.left ||
				a.left >= b.right ||
				a.bottom <= b.top ||
				a.top >= b.bottom
			);
		};

		const rectFromBounds = (left, top, right, bottom) => {
			if (![left, top, right, bottom].every((value) => typeof value === "number" && isFinite(value))) {
				return null;
			}
			if (right <= left || bottom <= top) return null;
			const width = right - left;
			const height = bottom - top;
			const centerX = Math.round((left + right) / 2);
			const centerY = Math.round((top + bottom) / 2);
			return {
				left: Math.round(left),
				top: Math.round(top),
				right: Math.round(right),
				bottom: Math.round(bottom),
				width: Math.round(width),
				height: Math.round(height),
				centerX: centerX,
				centerY: centerY,
				clickX: centerX,
				clickY: centerY,
				rawCenterX: centerX,
				rawCenterY: centerY,
			};
		};

		const isCollapsedElement = (el) => {
			if (!el) return null;
			const className = typeof el.className === "string" ? el.className.toLowerCase() : "";
			if (className.indexOf("collapsed") !== -1) return true;
			if (el.hidden) return true;
			if (el.getAttribute) {
				const ariaHidden = el.getAttribute("aria-hidden");
				if (ariaHidden === "true") return true;
				const ariaExpanded = el.getAttribute("aria-expanded");
				if (ariaExpanded === "false") return true;
			}
			try {
				const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
				if (style && (style.display === "none" || style.visibility === "hidden")) return true;
			} catch (err) {}
			return false;
		};

		const getStoreSection = (options) => {
			const contentEl = findFirstElement(options.contentSelectors || []);
			let toggleEl = findFirstElement(options.toggleSelectors || []);
			if (!toggleEl && options.labelPattern) {
				toggleEl = findFirstElementByText(
					options.labelSelectors || [],
					options.labelPattern
				);
			}
			const collapsed = isCollapsedElement(contentEl);
			return {
				toggle: getRect(toggleEl),
				rect: getRect(contentEl),
				collapsed: collapsed,
				visible: !!getRect(contentEl),
			};
		};

		const chooseFrom = (choices) => {
			if (!Array.isArray(choices) || choices.length === 0) return null;
			return choices[Math.floor(Math.random() * choices.length)];
		};
		const chooseFromRoll = (choices, randomFn) => {
			if (!Array.isArray(choices) || choices.length === 0) return null;
			const roll = typeof randomFn === "function" ? randomFn() : Math.random();
			return choices[Math.floor(roll * choices.length)];
		};
		const HAND_OF_FATE_LOOKAHEAD = 6;

		const getBuffNames = () => {
			if (!Game || !Game.buffs || typeof Game.buffs !== "object") return [];
			return Object.keys(Game.buffs).filter(Boolean).sort();
		};

		const getVisibleShimmerState = () => {
			const shimmers = Array.isArray(Game && Game.shimmers) ? Game.shimmers : [];
			const visible = shimmers.filter((shimmer) => shimmer && shimmer.l && shimmer.l.style.display !== "none");
			const visibleGolden = visible.filter((shimmer) => shimmer.type === "golden");
			const visibleWrath = visibleGolden.filter((shimmer) => !!shimmer.wrath);
			return {
				visibleShimmerCount: visible.length,
				visibleGoldenCount: visibleGolden.length,
				visibleWrathCount: visibleWrath.length,
				visibleShimmerIds: visible
					.map((shimmer) => (typeof shimmer.id === "number" ? shimmer.id : null))
					.filter((id) => id !== null),
				visibleGoldenIds: visibleGolden
					.map((shimmer) => (typeof shimmer.id === "number" ? shimmer.id : null))
					.filter((id) => id !== null),
				visibleWrathIds: visibleWrath
					.map((shimmer) => (typeof shimmer.id === "number" ? shimmer.id : null))
					.filter((id) => id !== null),
			};
		};

		const buildGoldenDecisionState = (me, shimmerType) => ({
			shimmerId: me && typeof me.id === "number" ? me.id : null,
			wrath: !!(me && me.wrath),
			force: me && typeof me.force === "string" && me.force ? me.force : "",
			season: Game && typeof Game.season === "string" ? Game.season : "",
			cookiesEarned: Game && typeof Game.cookiesEarned === "number" ? Game.cookiesEarned : 0,
			buildingsOwned: Game && typeof Game.BuildingsOwned === "number" ? Game.BuildingsOwned : 0,
			hasDragonflight: !!(Game && typeof Game.hasBuff === "function" && Game.hasBuff("Dragonflight")),
			hasScorn: !!(Game && typeof Game.hasGod === "function" && Game.hasGod("scorn")),
			canLumps: !!(Game && typeof Game.canLumps === "function" && Game.canLumps()),
			reaperOfFieldsMult: Game && typeof Game.auraMult === "function" ? Game.auraMult("Reaper of Fields") : 0,
			dragonflightMult: Game && typeof Game.auraMult === "function" ? Game.auraMult("Dragonflight") : 0,
			lastChoice: shimmerType && typeof shimmerType.last === "string" ? shimmerType.last : "",
			chain: shimmerType && typeof shimmerType.chain === "number" ? shimmerType.chain : 0,
			buffsBefore: getBuffNames(),
			...getVisibleShimmerState(),
		});

		const simulateGoldenChoice = (state, randomFn) => {
			const trace = [];
			const nextRandom = () => {
				const value = typeof randomFn === "function" ? randomFn() : Math.random();
				trace.push(value);
				return value;
			};
			let list = [];
			if (state.wrath) list.push("clot", "multiply cookies", "ruin cookies");
			else list.push("frenzy", "multiply cookies");
			if (state.wrath && state.hasScorn) list.push("clot", "ruin cookies", "clot", "ruin cookies");
			if (state.wrath && nextRandom() < 0.3) list.push("blood frenzy", "chain cookie", "cookie storm");
			else if (nextRandom() < 0.03 && state.cookiesEarned >= 100000) list.push("chain cookie", "cookie storm");
			if (nextRandom() < 0.05 && state.season === "fools") list.push("everything must go");
			if (nextRandom() < 0.1 && (nextRandom() < 0.05 || !state.hasDragonflight)) list.push("click frenzy");
			if (state.wrath && nextRandom() < 0.1) list.push("cursed finger");
			if (state.buildingsOwned >= 10 && nextRandom() < 0.25) list.push("building special");
			if (state.canLumps && nextRandom() < 0.0005) list.push("free sugar lump");
			if ((state.wrath === false && nextRandom() < 0.15) || nextRandom() < 0.05) {
				if (nextRandom() < state.reaperOfFieldsMult) list.push("dragon harvest");
				if (nextRandom() < state.dragonflightMult) list.push("dragonflight");
			}
			if (state.lastChoice && nextRandom() < 0.8 && list.indexOf(state.lastChoice) !== -1) {
				list.splice(list.indexOf(state.lastChoice), 1);
			}
			if (nextRandom() < 0.0001) list.push("blab");
			let choice = chooseFromRoll(list, nextRandom);
			if (state.chain > 0) choice = "chain cookie";
			if (state.force) choice = state.force;
			return {
				possibleChoices: list.slice(),
				choice: choice,
				randomTrace: trace,
				randomsUsed: trace.length,
			};
		};

		const classifyGoldenChoice = (decision) => {
			if (!decision || !decision.choice) return "unknown";
			if (!decision.wrath) return "allow";
			if (BLOCKED_WRATH_CHOICES.has(decision.choice)) return "block";
			if (RISKY_WRATH_CHOICES.has(decision.choice)) return "block";
			return "allow";
		};

		const recordGoldenDecision = (decision) => {
			lastGoldenDecision = decision;
			if (decision && decision.blocked) blockedGoldenDecisions += 1;
			goldenDecisionLog.push(decision);
			if (goldenDecisionLog.length > GOLDEN_DECISION_LOG_LIMIT) {
				goldenDecisionLog = goldenDecisionLog.slice(-GOLDEN_DECISION_LOG_LIMIT);
			}
		};

		const installGoldenDecisionHook = () => {
			if (!Game || !Game.shimmerTypes || !Game.shimmerTypes["golden"]) return false;
			const goldenType = Game.shimmerTypes["golden"];
			if (goldenType.__bridgeGoldenDecisionHookInstalled) return true;
			const originalPopFunc = goldenType.popFunc;
			if (typeof originalPopFunc !== "function") return false;
			goldenType.popFunc = function (me) {
				const preState = buildGoldenDecisionState(me, this);
				const cookiesBefore = typeof Game.cookies === "number" ? Game.cookies : null;
				const goldenClicksBefore = typeof Game.goldenClicks === "number" ? Game.goldenClicks : null;
				const nativeRandom = Math.random;
				const preview = simulateGoldenChoice(preState, nativeRandom);
				const gateDecision = classifyGoldenChoice({
					choice: preview.choice,
					wrath: preState.wrath,
				});
				const blocked = WRATH_GATE_ENABLED && gateDecision === "block";
				const trace = preview.randomTrace.slice();
				let replayIndex = 0;
				Math.random = function () {
					if (replayIndex < trace.length) {
						const value = trace[replayIndex];
						replayIndex += 1;
						return value;
					}
					return nativeRandom();
				};
				let result;
				const originalForce = me.force;
				if (blocked) {
					me.force = "blab";
				}
				try {
					result = originalPopFunc.call(this, me);
				} finally {
					me.force = originalForce;
					Math.random = nativeRandom;
				}
				recordGoldenDecision({
					timestamp: Date.now(),
					shimmerId: preState.shimmerId,
					wrath: preState.wrath,
					forced: !!preState.force,
					force: preState.force || null,
					predictorMode: WRATH_GATE_ENABLED ? "intercept_gate" : "observed_click_trace",
					preClickDeterministic: false,
					choice: preview.choice,
					appliedChoice: typeof this.last === "string" && this.last ? this.last : preview.choice,
					blocked: blocked,
					replayChoice: preview.choice,
					replayMatched: !preview.choice || !this.last ? null : preview.choice === this.last,
					possibleChoices: preview.possibleChoices,
					randomTrace: trace.slice(0, 24),
					randomsUsedForReplay: preview.randomsUsed,
					gateClassification: gateDecision,
					cookiesBefore: cookiesBefore,
					cookiesAfter: typeof Game.cookies === "number" ? Game.cookies : null,
					goldenClicksBefore: goldenClicksBefore,
					goldenClicksAfter: typeof Game.goldenClicks === "number" ? Game.goldenClicks : null,
					buffsBefore: preState.buffsBefore,
					buffsAfter: getBuffNames(),
					visibleShimmerCount: preState.visibleShimmerCount,
					visibleGoldenCount: preState.visibleGoldenCount,
					visibleWrathCount: preState.visibleWrathCount,
					visibleShimmerIds: preState.visibleShimmerIds,
					visibleGoldenIds: preState.visibleGoldenIds,
					visibleWrathIds: preState.visibleWrathIds,
				});
				if (me && me.l) {
					me.l.dataset.bridgeChoice = preview.choice || "";
					me.l.dataset.bridgeBlocked = blocked ? "1" : "0";
				}
				return result;
			};
			goldenType.__bridgeGoldenDecisionHookInstalled = true;
			return true;
		};

		const getBigCookie = () => {
			const el = document.getElementById("bigCookie");
			const rect = getRect(el);
			if (!rect) return null;
			return rect;
		};

		const getLumpTypeName = (type) => {
			if (type === 1) return "bifurcated";
			if (type === 2) return "golden";
			if (type === 3) return "meaty";
			if (type === 4) return "caramelized";
			return "normal";
		};

		const getLumpData = () => {
			try {
				if (!Game || typeof Game.canLumps !== "function") return null;
				const unlocked = !!Game.canLumps();
				const lumpsEl = document.getElementById("lumps");
				const rect = getRect(lumpsEl);
				const now = Date.now();
				const lumpT = typeof Game.lumpT === "number" ? Game.lumpT : null;
				const age = lumpT === null ? null : Math.max(0, now - lumpT);
				const matureAge = typeof Game.lumpMatureAge === "number" ? Game.lumpMatureAge : null;
				const ripeAge = typeof Game.lumpRipeAge === "number" ? Game.lumpRipeAge : null;
				const overripeAge = typeof Game.lumpOverripeAge === "number" ? Game.lumpOverripeAge : null;
				let stage = "locked";
				if (unlocked) {
					stage = "growing";
					if (age !== null && matureAge !== null && age >= matureAge) stage = "mature";
					if (age !== null && ripeAge !== null && age >= ripeAge) stage = "ripe";
					if (age !== null && overripeAge !== null && age >= overripeAge) stage = "overripe";
				}
				const modifiers = [];
				if (typeof Game.Has === "function" && Game.Has("Stevia Caelestis")) modifiers.push("Stevia Caelestis");
				if (typeof Game.Has === "function" && Game.Has("Diabetica Daemonicus")) modifiers.push("Diabetica Daemonicus");
				if (typeof Game.Has === "function" && Game.Has("Ichor syrup")) modifiers.push("Ichor syrup");
				if (typeof Game.Has === "function" && Game.Has("Sugar aging process")) modifiers.push("Sugar aging process");
				if (typeof Game.Has === "function" && Game.Has("Glucose-charged air")) modifiers.push("Glucose-charged air");
				if (typeof Game.auraMult === "function" && Game.auraMult("Dragon's Curve") > 0) {
					modifiers.push("Dragon's Curve");
				}
				if (typeof Game.hasGod === "function" && Game.BuildingsOwned % 10 === 0) {
					const godLvl = Game.hasGod("order");
					if (godLvl > 0) modifiers.push("Order");
				}
				return {
					unlocked: unlocked,
					target: rect,
					lumps: typeof Game.lumps === "number" ? Game.lumps : null,
					lumpsTotal: typeof Game.lumpsTotal === "number" ? Game.lumpsTotal : null,
					lumpT: lumpT,
					ageMs: age,
					matureAgeMs: matureAge,
					ripeAgeMs: ripeAge,
					overripeAgeMs: overripeAge,
					timeToMatureMs: age === null || matureAge === null ? null : Math.max(0, matureAge - age),
					timeToRipeMs: age === null || ripeAge === null ? null : Math.max(0, ripeAge - age),
					timeToOverripeMs: age === null || overripeAge === null ? null : Math.max(0, overripeAge - age),
					stage: stage,
					isMature: !!(age !== null && matureAge !== null && age >= matureAge),
					isRipe: !!(age !== null && ripeAge !== null && age >= ripeAge && (overripeAge === null || age < overripeAge)),
					currentType: typeof Game.lumpCurrentType === "number" ? Game.lumpCurrentType : 0,
					currentTypeName: getLumpTypeName(typeof Game.lumpCurrentType === "number" ? Game.lumpCurrentType : 0),
					refill: typeof Game.lumpRefill === "number" ? Game.lumpRefill : null,
					canRefill: typeof Game.canRefillLump === "function" ? !!Game.canRefillLump() : null,
					grandmas: Game.Objects && Game.Objects["Grandma"] ? (Game.Objects["Grandma"].amount || 0) : 0,
					modifiers: modifiers,
				};
			} catch (error) {
				console.error("shimmer bridge lump export failed", error);
				return null;
			}
		};

		const serializeShimmers = () => {
			if (!Game || !Array.isArray(Game.shimmers)) return [];
			return Game.shimmers
				.filter((s) => s && s.l && s.l.style.display !== "none")
				.map((s) => {
					const rect = getRect(s.l);
					if (!rect) return null;
					return {
						id: s.id,
						type: s.type || null,
						wrath: !!s.wrath,
						x: typeof s.x === "number" ? s.x : null,
						y: typeof s.y === "number" ? s.y : null,
						width: rect.width,
						height: rect.height,
						left: rect.left,
						top: rect.top,
						centerX: rect.centerX,
						centerY: rect.centerY,
						rawCenterX: rect.rawCenterX,
						rawCenterY: rect.rawCenterY,
						life: typeof s.life === "number" ? s.life : null,
						dur: typeof s.dur === "number" ? s.dur : null,
						spawnLead: !!s.spawnLead,
						noCount: !!s.noCount,
						force: typeof s.force === "string" && s.force ? s.force : null,
						forceObjType: s.forceObj && typeof s.forceObj.type === "string" ? s.forceObj.type : null,
					};
				})
				.filter(Boolean);
		};

		const getFortuneData = () => {
			if (!Game || !Game.TickerEffect || Game.TickerEffect.type !== "fortune") return null;
			const tickerEl = Game.tickerL || document.getElementById("commentsText1");
			if (!tickerEl) return null;
			let fortuneEl = null;
			try {
				fortuneEl = tickerEl.querySelector ? tickerEl.querySelector(".fortune") : null;
			} catch (err) {
				fortuneEl = null;
			}
			const rect = getRect(fortuneEl || tickerEl);
			if (!rect) return null;
			const effect = Game.TickerEffect.sub;
			const effectKind =
				effect === "fortuneGC" || effect === "fortuneCPS"
					? effect
					: effect && typeof effect.name === "string"
						? "upgrade"
						: null;
			return {
				id: -100000 - (typeof Game.TickerN === "number" ? Game.TickerN : 0),
				type: "fortune",
				wrath: false,
				width: rect.width,
				height: rect.height,
				left: rect.left,
				top: rect.top,
				centerX: rect.centerX,
				centerY: rect.centerY,
				clickX: rect.clickX,
				clickY: rect.clickY,
				rawCenterX: rect.rawCenterX,
				rawCenterY: rect.rawCenterY,
				life: typeof Game.TickerAge === "number" ? Game.TickerAge : null,
				dur: typeof Game.fps === "number" ? Game.fps * 10 : null,
				effectKind: effectKind,
				effectName: effect && typeof effect.name === "string" ? effect.name : effectKind,
				effectId: effect && typeof effect.id === "number" ? effect.id : null,
				text: stripHtml(tickerEl.textContent || tickerEl.innerText || ""),
			};
		};

		const getSpellRect = (spellId) => {
			const spellEl = document.getElementById("grimoireSpell" + spellId);
			return getRect(spellEl);
		};

		const getSpellForecast = (minigame, spellKey, castIndex) => {
			if (
				!Game ||
				!minigame ||
				!minigame.spells ||
				!minigame.spells[spellKey] ||
				typeof minigame.getFailChance !== "function" ||
				typeof Math.seedrandom !== "function"
			) {
				return null;
			}

			const spell = minigame.spells[spellKey];
			const failChance = minigame.getFailChance(spell);
			if (typeof castIndex !== "number") return null;
			const goldenCount =
				Game.shimmerTypes &&
				Game.shimmerTypes["golden"] &&
				typeof Game.shimmerTypes["golden"].n === "number"
					? Game.shimmerTypes["golden"].n
					: 0;
			Math.seedrandom(Game.seed + "/" + castIndex);
			const backfire = Math.random() >= 1 - failChance;
			let outcome = null;
			let choices = [];
			if (spellKey === "hand of fate") {
				const hasDragonflight = !!(Game.hasBuff && Game.hasBuff("Dragonflight"));
				const buildingsOwned = typeof Game.BuildingsOwned === "number" ? Game.BuildingsOwned : 0;
				if (!backfire) {
					choices.push("frenzy", "multiply cookies");
					if (!hasDragonflight) choices.push("click frenzy");
					if (Math.random() < 0.1) choices.push("cookie storm", "cookie storm", "blab");
					if (buildingsOwned >= 10 && Math.random() < 0.25) choices.push("building special");
					if (Math.random() < 0.15) choices = ["cookie storm drop"];
					if (Math.random() < 0.0001) choices.push("free sugar lump");
					outcome = chooseFrom(choices);
				} else {
					choices.push("clot", "ruin cookies");
					if (Math.random() < 0.1) choices.push("cursed finger", "blood frenzy");
					if (Math.random() < 0.003) choices.push("free sugar lump");
					if (Math.random() < 0.1) choices = ["blab"];
					outcome = chooseFrom(choices);
				}
			}
			Math.seedrandom();

			return {
				castIndex: castIndex,
				failChance: typeof failChance === "number" ? failChance : null,
				backfire: backfire,
				outcome: outcome,
				choices: choices,
				goldenCookiesOnScreen: goldenCount,
			};
		};

		const getSpellForecasts = (minigame) => {
			if (!minigame || typeof minigame.spellsCastTotal !== "number") return null;
			const spellKeys =
				minigame.spells && typeof minigame.spells === "object" ? Object.keys(minigame.spells) : [];
			const out = [];
			for (let offset = 0; offset < HAND_OF_FATE_LOOKAHEAD; offset++) {
				const castIndex = minigame.spellsCastTotal + offset;
				const spells = {};
				for (let i = 0; i < spellKeys.length; i++) {
					const key = spellKeys[i];
					spells[key] = getSpellForecast(minigame, key, castIndex);
				}
				out.push({
					offset: offset,
					castIndex: castIndex,
					handOfFate: spells["hand of fate"] || null,
					hagglersCharm: spells["haggler's charm"] || null,
					spells: spells,
				});
			}
			return out;
		};

		const getSpellbookData = () => {
			if (!Game || !Game.Objects || !Game.Objects["Wizard tower"]) return null;
			const tower = Game.Objects["Wizard tower"];
			const minigame = tower.minigame;
			if (!minigame || !minigame.spells || !minigame.getSpellCost) return null;
			const onMinigame = !!tower.onMinigame;
			const id = typeof tower.id === "number" ? tower.id : null;
			let openSelectors = [
				"#wizardTowerMinigameButton",
				"#grimoireMinigameButton",
				"[data-minigame='grimoire']",
				"[data-minigame='wizard tower']",
				"[data-minigame='Wizard tower']",
			];
			if (id !== null) {
				openSelectors = openSelectors.concat([
					"#productMinigameButton" + id,
					"#rowSpecial" + id,
					"#specialButton" + id,
					"#specialPopupButton" + id,
				]);
			}
			const openControl = getRectBySelectors(openSelectors);

			const spells = Object.keys(minigame.spells)
				.map((key) => {
					const spell = minigame.spells[key];
					if (!spell || typeof spell.id !== "number") return null;
					const rect = onMinigame ? getSpellRect(spell.id) : null;
					const cost = minigame.getSpellCost(spell);
					const failChance =
						typeof minigame.getFailChance === "function" ? minigame.getFailChance(spell) : null;
					const spellEl = onMinigame ? document.getElementById("grimoireSpell" + spell.id) : null;
					const ready =
						(!onMinigame || !!rect) &&
						typeof cost === "number" &&
						minigame.magic >= cost &&
						(!onMinigame || (!!spellEl && spellEl.className.indexOf("ready") !== -1));
					return {
						id: spell.id,
						key: key,
						name: spell.name || key,
						cost: typeof cost === "number" ? cost : null,
						failChance: typeof failChance === "number" ? failChance : null,
						ready: ready,
						rect: rect,
					};
				})
				.filter(Boolean);

			const activeBuffs = getActiveBuffs();
			const handOfFateForecast = getSpellForecast(minigame, "hand of fate", minigame.spellsCastTotal);
			const spellForecasts = getSpellForecasts(minigame);

			return {
				onMinigame: onMinigame,
				openControl: openControl,
				magic: typeof minigame.magic === "number" ? minigame.magic : null,
				maxMagic: typeof minigame.magicM === "number" ? minigame.magicM : null,
				spellsCast: typeof minigame.spellsCast === "number" ? minigame.spellsCast : null,
				spellsCastTotal: typeof minigame.spellsCastTotal === "number" ? minigame.spellsCastTotal : null,
				magicRegenPerSecond:
					typeof minigame.magic === "number" &&
					typeof minigame.magicM === "number" &&
					typeof Game.fps === "number"
						? Math.max(0.002, Math.pow(minigame.magic / Math.max(minigame.magicM, 100), 0.5)) * 0.002 * Game.fps
						: null,
				spells: spells,
				activeBuffs: activeBuffs,
				handOfFateForecast: handOfFateForecast,
				spellForecasts: spellForecasts,
			};
		};

		const getActiveBuffs = () => {
			if (!Game || !Game.buffs) return [];
			return Object.keys(Game.buffs)
				.map((key) => {
					const buff = Game.buffs[key];
					if (!buff) return null;
					const buffType = buff.type ? buff.type.name || null : null;
					let buildingId = null;
					let buildingName = null;
					if (
						(buffType === "building buff" || buffType === "building debuff") &&
						typeof buff.arg2 === "number" &&
						Game.ObjectsById &&
						Game.ObjectsById[buff.arg2]
					) {
						buildingId = buff.arg2;
						buildingName = Game.ObjectsById[buff.arg2].name || null;
					}
					return {
						key: key,
						name: buff.name || key,
						time: typeof buff.time === "number" ? buff.time : null,
						maxTime: typeof buff.maxTime === "number" ? buff.maxTime : null,
						multCpS: typeof buff.multCpS === "number" ? buff.multCpS : null,
						multClick: typeof buff.multClick === "number" ? buff.multClick : null,
						type: buffType,
						power: typeof buff.power === "number" ? buff.power : null,
						buildingId: buildingId,
						buildingName: buildingName,
					};
				})
				.filter(Boolean);
		};

		const getWrinklerRewardMultiplier = (me) => {
			if (!Game) return 1.1;
			let multiplier = 1.1;
			if (Game.Has && Game.Has("Sacrilegious corruption")) multiplier *= 1.05;
			if (typeof Game.auraMult === "function") multiplier *= 1 + Game.auraMult("Dragon Guts") * 0.2;
			if (me && me.type === 1) multiplier *= 3;
			if (Game.Has && Game.Has("Wrinklerspawn")) multiplier *= 1.05;
			if (typeof Game.hasGod === "function") {
				const godLvl = Game.hasGod("scorn");
				if (godLvl === 1) multiplier *= 1.15;
				else if (godLvl === 2) multiplier *= 1.1;
				else if (godLvl === 3) multiplier *= 1.05;
			}
			return multiplier;
		};

		const getPreferredSpell = (spellbook) => {
			if (!spellbook || !Array.isArray(spellbook.spells)) return null;
			for (let i = 0; i < spellbook.spells.length; i++) {
				const spell = spellbook.spells[i];
				if (spell && spell.key === "hand of fate") return spell;
			}
			return null;
		};

		const getBankOpenControl = (bank) => {
			const id = bank && typeof bank.id === "number" ? bank.id : null;
			let selectors = [
				"#bankMinigameButton",
				"#bankSwitch",
				"#bankButton",
				"[data-minigame='bank']",
				"[data-minigame='Bank']",
			];
			if (id !== null) {
				selectors = ["#productMinigameButton" + id].concat(selectors, [
					"#rowSpecial" + id,
					"#specialButton" + id,
					"#specialPopupButton" + id,
				]);
			}
			return getRectBySelectors(selectors);
		};

		const getBankBrokerControl = () =>
			getRectBySelectors([
				"#bankBrokersBuy",
				"#bankBrokerBuy",
				"#bankBrokersButton",
				".bankBrokersBuy",
			]);

		const getBankBrokerControlElement = () =>
			findFirstElement([
				"#bankBrokersBuy",
				"#bankBrokerBuy",
				"#bankBrokersButton",
				".bankBrokersBuy",
			]);

		const getBankOfficeUpgradeControl = () =>
			getRectBySelectors([
				"#bankOfficeUpgrade",
				"#bankOfficeButton",
				"#bankOfficeBuy",
				".bankOfficeUpgrade",
			]);

		const getBankOfficeUpgradeControlElement = () =>
			findFirstElement([
				"#bankOfficeUpgrade",
				"#bankOfficeButton",
				"#bankOfficeBuy",
				".bankOfficeUpgrade",
			]);

		const getBankGoodControls = (index) => {
			const rowSelectors = [
				"#bankGood-" + index,
				"#bankGood" + index,
				"#bankRow-" + index,
				"#bankRow" + index,
			];
			const rowEl = findFirstElement(rowSelectors);
			const rowRect = getRect(rowEl);
			let buy1El = null;
			let buy10El = null;
			let buy100El = null;
			let buyMaxEl = null;
			let sell1El = null;
			let sell10El = null;
			let sell100El = null;
			let sellAllEl = null;

			if (rowEl && rowEl.querySelector) {
				buy1El = rowEl.querySelector("#bankGood-" + index + "_1");
				buy10El = rowEl.querySelector("#bankGood-" + index + "_10");
				buy100El = rowEl.querySelector("#bankGood-" + index + "_100");
				buyMaxEl =
					rowEl.querySelector("[id$='_Max']") ||
					rowEl.querySelector(".bankButtonBuy[id*='_Max']");
				sell1El = rowEl.querySelector("#bankGood-" + index + "_-1");
				sell10El = rowEl.querySelector("#bankGood-" + index + "_-10");
				sell100El = rowEl.querySelector("#bankGood-" + index + "_-100");
				sellAllEl =
					rowEl.querySelector("[id$='_-All']") ||
					rowEl.querySelector(".bankButtonSell[id*='_-All']");
			}

			if (!buy1El) buy1El = findFirstElement(["#bankGood-" + index + "_1"]);
			if (!buy10El) buy10El = findFirstElement(["#bankGood-" + index + "_10"]);
			if (!buy100El) buy100El = findFirstElement(["#bankGood-" + index + "_100"]);
			if (!buyMaxEl) {
				buyMaxEl = findFirstElement([
					"#bankGood-" + index + "_Max",
					"#bankGood" + index + "_Max",
				]);
			}
			if (!sell1El) sell1El = findFirstElement(["#bankGood-" + index + "_-1"]);
			if (!sell10El) sell10El = findFirstElement(["#bankGood-" + index + "_-10"]);
			if (!sell100El) sell100El = findFirstElement(["#bankGood-" + index + "_-100"]);
			if (!sellAllEl) {
				sellAllEl = findFirstElement([
					"#bankGood-" + index + "_-All",
					"#bankGood" + index + "_-All",
				]);
			}

			return {
				row: rowRect,
				buy: getRect(buy1El),
				buy1: getRect(buy1El),
				buy10: getRect(buy10El),
				buy100: getRect(buy100El),
				buyMax: getRect(buyMaxEl),
				sell: getRect(sell1El),
				sell1: getRect(sell1El),
				sell10: getRect(sell10El),
				sell100: getRect(sell100El),
				sellAll: getRect(sellAllEl),
				canBuy: isElementEnabled(buy1El),
				canBuy1: isElementEnabled(buy1El),
				canBuy10: isElementEnabled(buy10El),
				canBuy100: isElementEnabled(buy100El),
				canBuyMax: isElementEnabled(buyMaxEl),
				canSell: isElementEnabled(sell1El),
				canSell1: isElementEnabled(sell1El),
				canSell10: isElementEnabled(sell10El),
				canSell100: isElementEnabled(sell100El),
				canSellAll: isElementEnabled(sellAllEl),
			};
		};

		const getBankData = () => {
			if (!Game || !Game.Objects || !Game.Objects["Bank"]) return null;
			const bank = Game.Objects["Bank"];
			const minigame = bank.minigame;
			if (!minigame || !Array.isArray(minigame.goodsById)) return null;
			const onMinigame = !!bank.onMinigame;
			const secondsPerTick =
				typeof minigame.secondsPerTick === "number" ? minigame.secondsPerTick : null;
			const tickFramesRemaining =
				typeof minigame.tickT === "number" && typeof Game.fps === "number" && typeof secondsPerTick === "number"
					? Math.max(0, (Game.fps * secondsPerTick) - minigame.tickT)
					: null;
			const nextTickAt =
				typeof tickFramesRemaining === "number" && typeof Game.fps === "number"
					? Date.now() + Math.round((tickFramesRemaining / Game.fps) * 1000)
					: null;

			const brokerControlEl = getBankBrokerControlElement();
			const officeUpgradeControlEl = getBankOfficeUpgradeControlElement();
			const currentOffice =
				typeof minigame.officeLevel === "number" &&
				Array.isArray(minigame.offices) &&
				minigame.offices[minigame.officeLevel]
					? minigame.offices[minigame.officeLevel]
					: null;
			const nextOffice =
				typeof minigame.officeLevel === "number" &&
				Array.isArray(minigame.offices) &&
				minigame.offices[minigame.officeLevel + 1]
					? minigame.offices[minigame.officeLevel + 1]
					: null;
			const currentOfficeCost =
				currentOffice && Array.isArray(currentOffice.cost) ? currentOffice.cost : null;

			return {
				onMinigame: !!bank.onMinigame,
				openControl: getBankOpenControl(bank),
				officeLevel: typeof minigame.officeLevel === "number" ? minigame.officeLevel : null,
				officeName:
					currentOffice ? currentOffice.name || null : null,
				profit: typeof minigame.profit === "number" ? minigame.profit : null,
				brokers: minigame.brokers,
				brokersMax: minigame.getMaxBrokers ? minigame.getMaxBrokers() : null,
				brokerCost:
					typeof minigame.getBrokerPrice === "function" ? minigame.getBrokerPrice() : null,
				brokerControl: getBankBrokerControl(),
				canHireBroker: isElementEnabled(brokerControlEl),
				nextOfficeLevel:
					typeof minigame.officeLevel === "number" ? minigame.officeLevel + 1 : null,
				nextOfficeName: nextOffice ? nextOffice.name || null : null,
				officeUpgradeCost: currentOfficeCost ? currentOfficeCost[0] : null,
				officeUpgradeCursorLevel: currentOfficeCost ? currentOfficeCost[1] : null,
				officeUpgradeControl: getBankOfficeUpgradeControl(),
				canUpgradeOffice: isElementEnabled(officeUpgradeControlEl),
				ticks: typeof minigame.ticks === "number" ? minigame.ticks : null,
				tickFrames: typeof minigame.tickT === "number" ? minigame.tickT : null,
				secondsPerTick: secondsPerTick,
				nextTickAt: nextTickAt,
				goods: minigame.goodsById.map((good, index) => {
					if (!good) return null;
					const controls = onMinigame
						? getBankGoodControls(index)
						: {
							row: null,
							buy: null,
							buy1: null,
							buy10: null,
							buy100: null,
							buyMax: null,
							sell: null,
							sell1: null,
							sell10: null,
							sell100: null,
							sellAll: null,
							canBuy: false,
							canBuy1: false,
							canBuy10: false,
							canBuy100: false,
							canBuyMax: false,
							canSell: false,
							canSell1: false,
							canSell10: false,
							canSell100: false,
							canSellAll: false,
						};
					const maxStock = minigame.getGoodMaxStock ? minigame.getGoodMaxStock(good) : null;
					const restingValue =
						minigame.getRestingVal && typeof minigame.getRestingVal === "function"
							? minigame.getRestingVal(index)
							: null;
					const history =
						Array.isArray(good.vals)
							? good.vals
								.slice(0, 16)
								.map((value) => (typeof value === "number" ? value : null))
								.filter((value) => value !== null)
							: [];
					return {
						id: index,
						symbol: good.symbol || null,
						name: good.name || null,
						icon: Array.isArray(good.icon) ? good.icon.slice(0, 2) : null,
						active: !!good.active,
						hidden: !!good.hidden,
						value: typeof good.val === "number" ? good.val : null,
						restingValue: typeof restingValue === "number" ? restingValue : null,
						stock: typeof good.stock === "number" ? good.stock : null,
						stockMax: typeof maxStock === "number" ? maxStock : null,
						mode: typeof good.mode === "number" ? good.mode : null,
						modeName:
							typeof good.mode === "number"
								? ["stable", "slow_rise", "slow_fall", "fast_rise", "fast_fall", "chaotic"][good.mode] || null
								: null,
						modeTicksRemaining: typeof good.dur === "number" ? good.dur : null,
						last: typeof good.last === "number" ? good.last : null,
						delta: typeof good.d === "number" ? good.d : null,
						history: history,
						row: controls.row,
						buy: controls.buy,
						buy1: controls.buy1,
						buy10: controls.buy10,
						buy100: controls.buy100,
						sell: controls.sell,
						sell1: controls.sell1,
						sell10: controls.sell10,
						sell100: controls.sell100,
						buyMax: controls.buyMax,
						sellAll: controls.sellAll,
						canBuy: controls.canBuy,
						canBuy1: controls.canBuy1,
						canBuy10: controls.canBuy10,
						canBuy100: controls.canBuy100,
						canSell: controls.canSell,
						canSell1: controls.canSell1,
						canSell10: controls.canSell10,
						canSell100: controls.canSell100,
						canBuyMax: controls.canBuyMax,
						canSellAll: controls.canSellAll,
					};
				}).filter(Boolean),
			};
		};

		const getProductsViewport = () => {
			const sectionRect = getRect(findFirstElement(["#sectionRight", "#store"]));
			if (!sectionRect) return null;
			const controls = [
				getRectBySelectors(["#storeBulk"]),
				getRectBySelectors(["#storeBulkBuy"]),
				getRectBySelectors(["#storeBulkSell"]),
				getRectBySelectors(["#storeBulk1"]),
				getRectBySelectors(["#storeBulk10"]),
				getRectBySelectors(["#storeBulk100"]),
				getRectBySelectors(["#storeBulkMax"]),
			].filter(Boolean);
			const controlBottom = controls.reduce(
				(maxBottom, rect) => Math.max(maxBottom, typeof rect.bottom === "number" ? rect.bottom : maxBottom),
				sectionRect.top
			);
			const productRows = Array.isArray(Game && Game.ObjectsById)
				? Game.ObjectsById
					.map((building) => getRect(findFirstElement([
						"#product" + (building && typeof building.id === "number" ? building.id : ""),
					])))
					.filter(Boolean)
				: [];
			const visibleRows = productRows.filter(
				(rect) => rectIntersects(rect, sectionRect) && rect.bottom > controlBottom
			);
			if (visibleRows.length > 0) {
				const top = Math.max(
					controlBottom + 8,
					Math.min.apply(null, visibleRows.map((rect) => rect.top))
				);
				const bottom = Math.min(
					sectionRect.bottom,
					Math.max.apply(null, visibleRows.map((rect) => rect.bottom))
				);
				const viewportRect = rectFromBounds(sectionRect.left, top, sectionRect.right, bottom);
				if (viewportRect) return assignProductsViewportScrollAnchor(viewportRect, controlBottom);
			}
			return assignProductsViewportScrollAnchor(
				rectFromBounds(sectionRect.left, controlBottom + 8, sectionRect.right, sectionRect.bottom),
				controlBottom
			);
		};

		const assignProductsViewportScrollAnchor = (viewportRect, controlBottom) => {
			if (!viewportRect) return null;
			const inset = 12;
			const minX = Math.round(viewportRect.left + inset);
			const maxX = Math.round(viewportRect.right - inset);
			const minY = Math.round(Math.max(viewportRect.top + inset, controlBottom + 12));
			const maxY = Math.round(viewportRect.bottom - inset);
			const preferredX = Math.round(viewportRect.left + (viewportRect.width || (viewportRect.right - viewportRect.left)) * 0.45);
			const preferredY = Math.round(minY + Math.max(0, maxY - minY) * 0.5);
			viewportRect.clickX = Math.max(minX, Math.min(maxX, preferredX));
			viewportRect.clickY = Math.max(minY, Math.min(maxY, preferredY));
			viewportRect.centerX = viewportRect.clickX;
			viewportRect.centerY = viewportRect.clickY;
			return viewportRect;
		};

		const getBuildingTarget = (id) => {
			const rowEl = findFirstElement([
				"#product" + id,
				"#products .product[data-id='" + id + "']",
			]);
			const rowRect = getRect(rowEl);
			if (!rowRect) return null;
			const iconRect = getRect(findFirstElement(["#productIcon" + id]));
			const nameRect = getRect(findFirstElement(["#productName" + id]));
			const targetRect = {
				...rowRect,
			};
			const minX = Math.round(rowRect.left + 24);
			const maxX = Math.round(rowRect.right - 24);
			const minY = Math.round(rowRect.top + 8);
			const maxY = Math.round(rowRect.bottom - 8);
			const preferredX = Math.round(rowRect.left + rowRect.width * 0.45);
			const preferredY = rowRect.centerY;
			targetRect.centerX = Math.max(minX, Math.min(maxX, preferredX));
			targetRect.centerY = Math.max(minY, Math.min(maxY, preferredY));
			targetRect.clickX = targetRect.centerX;
			targetRect.clickY = targetRect.centerY;
			return targetRect;
		};

		const getBuildingsData = () => {
			if (!Game || !Array.isArray(Game.ObjectsById)) return [];
			const productsViewport = getProductsViewport();
			return Game.ObjectsById
				.filter((building) => building && typeof building.id === "number")
				.map((building) => {
					const target = getBuildingTarget(building.id);
					const currentPrice =
						typeof building.getPrice === "function" ? building.getPrice() : building.price;
					const sumPrice10 =
						typeof building.getSumPrice === "function" ? building.getSumPrice(10) : null;
					const sumPrice100 =
						typeof building.getSumPrice === "function" ? building.getSumPrice(100) : null;
					const sellValue1 =
						typeof building.getReverseSumPrice === "function" ? building.getReverseSumPrice(1) : null;
					const sellValue10 =
						typeof building.getReverseSumPrice === "function" ? building.getReverseSumPrice(10) : null;
					const sellValue100 =
						typeof building.getReverseSumPrice === "function" ? building.getReverseSumPrice(100) : null;
					return {
						id: building.id,
						name: building.name || null,
						amount: typeof building.amount === "number" ? building.amount : 0,
						level: typeof building.level === "number" ? building.level : 0,
						price: typeof currentPrice === "number" ? currentPrice : null,
						sumPrice10: typeof sumPrice10 === "number" ? sumPrice10 : null,
						sumPrice100: typeof sumPrice100 === "number" ? sumPrice100 : null,
						bulkPrice: typeof building.bulkPrice === "number" ? building.bulkPrice : null,
						basePrice: typeof building.basePrice === "number" ? building.basePrice : null,
						storedCps: typeof building.storedCps === "number" ? building.storedCps : null,
						storedTotalCps: typeof building.storedTotalCps === "number" ? building.storedTotalCps : null,
						sellValue1: typeof sellValue1 === "number" ? sellValue1 : null,
						sellValue10: typeof sellValue10 === "number" ? sellValue10 : null,
						sellValue100: typeof sellValue100 === "number" ? sellValue100 : null,
						sellMultiplier: typeof building.getSellMultiplier === "function" ? building.getSellMultiplier() : null,
						locked: !!building.locked,
						canBuy: !building.locked && !!target && typeof currentPrice === "number" && Game.cookies >= currentPrice,
						canSell: !!target && typeof building.amount === "number" && building.amount > 0,
						visible: !!target && !!productsViewport && rectIntersects(target, productsViewport),
						row: target,
						target: target,
					};
				});
		};

		const getUpgradeTarget = (storeIndex) => {
			const avoidRects = [
				getRectBySelectors(["#storeBulkBuy"]),
				getRectBySelectors(["#storeBulkSell"]),
				getRectBySelectors(["#storeBulk1"]),
				getRectBySelectors(["#storeBulk10"]),
				getRectBySelectors(["#storeBulk100"]),
				getRectBySelectors(["#storeBulkMax"]),
			].filter(Boolean);
			const upgradeEl = document.getElementById("upgrade" + storeIndex);
			const rect = getRect(upgradeEl);
			if (!rect) return null;
			const safePoint = chooseSafePointInRect(rect, avoidRects);
			if (safePoint) {
				rect.centerX = safePoint[0];
				rect.centerY = safePoint[1];
				rect.clickX = safePoint[0];
				rect.clickY = safePoint[1];
			}
			return rect;
		};

		const getUpgradesData = () => {
			if (!Game || !Array.isArray(Game.UpgradesInStore)) return [];
			const productsViewport = getProductsViewport();
			return Game.UpgradesInStore
				.map((upgrade, index) => {
					if (!upgrade || typeof upgrade.id !== "number" || upgrade.bought) return null;
					const target = getUpgradeTarget(index);
					const price = typeof upgrade.getPrice === "function" ? upgrade.getPrice() : upgrade.basePrice;
					const rawPower = typeof upgrade.power === "function" ? null : upgrade.power;
					const buildingTie =
						upgrade.buildingTie && typeof upgrade.buildingTie === "object"
							? upgrade.buildingTie
							: upgrade.buildingTie1 && typeof upgrade.buildingTie1 === "object"
								? upgrade.buildingTie1
								: null;
					return {
						id: upgrade.id,
						storeIndex: index,
						name: upgrade.name || null,
						displayName: upgrade.dname || upgrade.name || null,
						pool: upgrade.pool || null,
						power: typeof rawPower === "number" ? rawPower : null,
						tier: upgrade.tier || null,
						kitten: !!upgrade.kitten,
						buildingTieId: buildingTie && typeof buildingTie.id === "number" ? buildingTie.id : null,
						buildingTieName: buildingTie && typeof buildingTie.name === "string" ? buildingTie.name : null,
						price: typeof price === "number" ? price : null,
						deltaCps: null,
						paybackSeconds: null,
						canBuy: typeof upgrade.canBuy === "function" ? !!upgrade.canBuy() : false,
						unlocked: !!upgrade.unlocked,
						visible: !!target && !!productsViewport && rectIntersects(target, productsViewport),
						target: target,
						row: target,
					};
				})
				.filter(Boolean);
		};

		const getBestUpgrade = (upgrades) => {
			if (!Array.isArray(upgrades) || upgrades.length === 0) return null;
			const paybackCandidates = upgrades.filter(
				(upgrade) =>
					upgrade &&
					typeof upgrade.price === "number" &&
					typeof upgrade.deltaCps === "number" &&
					typeof upgrade.paybackSeconds === "number" &&
					upgrade.deltaCps > 0 &&
					upgrade.paybackSeconds > 0
			);
			if (paybackCandidates.length > 0) {
				paybackCandidates.sort((a, b) => {
					if (a.paybackSeconds !== b.paybackSeconds) return a.paybackSeconds - b.paybackSeconds;
					if (a.price !== b.price) return a.price - b.price;
					return a.id - b.id;
				});
				return paybackCandidates[0];
			}
			const visibleAffordable = upgrades.filter(
				(upgrade) =>
					upgrade &&
					upgrade.canBuy &&
					typeof upgrade.price === "number" &&
					isFinite(upgrade.price)
			);
			if (visibleAffordable.length === 0) return null;
			visibleAffordable.sort((a, b) => {
				if (a.price !== b.price) return a.price - b.price;
				return a.id - b.id;
			});
			return visibleAffordable[0];
		};

		const getAscensionData = () => {
			if (!Game || typeof Game.HowManyCookiesReset !== "function") return null;

			const cookiesEarned = typeof Game.cookiesEarned === "number" ? Game.cookiesEarned : 0;
			const cookiesReset = typeof Game.cookiesReset === "number" ? Game.cookiesReset : 0;
			const lifetimeCookies = cookiesEarned + cookiesReset;
			const bankedPrestige = typeof Game.prestige === "number"
				? Math.max(0, Math.floor(Game.prestige))
				: 0;
			let ascendGain = typeof Game.ascendMeterLevel === "number" ? Math.max(0, Math.floor(Game.ascendMeterLevel)) : null;
			if (!Number.isFinite(ascendGain) || ascendGain > 1e20) {
				if (typeof Game.HowMuchPrestige === "function") {
					const currentPrestigeFallback = Math.max(0, Math.floor(Game.HowMuchPrestige(lifetimeCookies)));
					ascendGain = Math.max(0, currentPrestigeFallback - bankedPrestige);
				} else {
					ascendGain = 0;
				}
			}
			const currentPrestige = bankedPrestige + ascendGain;
			const currentChipStart = Game.HowManyCookiesReset(currentPrestige);
			const nextChipTotal = Game.HowManyCookiesReset(currentPrestige + 1);
			const legacySpan = Math.max(1, nextChipTotal - currentChipStart);
			const cookiesToNextLegacy = Math.max(0, nextChipTotal - lifetimeCookies);
			const targetLegacyMeterPercent =
				typeof Game.ascendMeterPercentT === "number" && Number.isFinite(Game.ascendMeterPercentT)
					? Game.ascendMeterPercentT
					: 1 - (cookiesToNextLegacy / legacySpan);
			const legacyMeterPercent = Math.max(0, Math.min(1, targetLegacyMeterPercent));
			const currentLevelStart = currentChipStart;
			const nextLevelTarget = nextChipTotal;
			const levelProgress = legacyMeterPercent;

			return {
				cookiesEarned: cookiesEarned,
				cookiesReset: cookiesReset,
				lifetimeCookies: lifetimeCookies,
				currentPrestige: currentPrestige,
				bankedPrestige: bankedPrestige,
				ascendGain: ascendGain,
				ascendNowToGet: ascendGain,
				nextPrestige: currentPrestige + 1,
				nextPrestigeCookies: nextLevelTarget,
				currentLevelStartCookies: currentLevelStart,
				levelProgress: levelProgress,
				cookiesToNextPrestige: Math.max(0, nextLevelTarget - lifetimeCookies),
				legacyMeterPercent: legacyMeterPercent,
				legacyMeterStartCookies: currentChipStart,
				legacyMeterTargetCookies: nextChipTotal,
				cookiesToNextLegacyChip: cookiesToNextLegacy,
				heavenlyChips: typeof Game.heavenlyChips === "number" ? Game.heavenlyChips : null,
			};
		};

		const stripHtml = (value) => {
			if (typeof value !== "string") return value == null ? null : String(value);
			return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
		};

		const getSpecialTabRect = (name) => {
			if (!Game || !Array.isArray(Game.specialTabs) || !Game.specialTabs.length) return null;
			const index = Game.specialTabs.indexOf(name);
			if (index < 0) return null;
			const canvasEl = document.getElementById("backgroundLeftCanvas");
			const canvasRect = getRect(canvasEl);
			if (!canvasRect || typeof canvasEl.height !== "number" || canvasEl.height <= 0) return null;
			const len = Game.specialTabs.length;
			const centerY = Math.round(canvasRect.top + (canvasEl.height - 24 - 48 * len) + (index * 48));
			const centerX = Math.round(canvasRect.left + 32);
			return {
				left: centerX - 20,
				top: centerY - 20,
				right: centerX + 20,
				bottom: centerY + 20,
				width: 40,
				height: 40,
				centerX: centerX,
				centerY: centerY,
				clickX: centerX,
				clickY: centerY,
				rawCenterX: centerX,
				rawCenterY: centerY,
			};
		};

		const getClosestPromptRoot = (el) => {
			if (!el) return null;
			if (typeof el.closest === "function") {
				const closestPrompt = el.closest(".prompt");
				if (closestPrompt) return closestPrompt;
			}
			let current = el.parentElement || null;
			while (current) {
				const className =
					typeof current.className === "string"
						? current.className
						: current.className && typeof current.className.baseVal === "string"
							? current.className.baseVal
							: "";
				if (className.indexOf("prompt") !== -1) return current;
				current = current.parentElement || null;
			}
			return null;
		};

		const getInlineHandlerMatch = (el, pattern) => {
			if (!el || !pattern) return null;
			const attrs = typeof el.getAttributeNames === "function" ? el.getAttributeNames() : [];
			for (let i = 0; i < attrs.length; i++) {
				const value = el.getAttribute(attrs[i]);
				if (typeof value !== "string") continue;
				const match = value.match(pattern);
				if (match) return match;
			}
			return null;
		};

		const getDragonAuraSlotControl = (slot) => {
			const popup = document.getElementById("specialPopup");
			if (!popup) return null;
			let nodes = [];
			try {
				nodes = Array.from(popup.querySelectorAll(".crate.enabled,.crate"));
			} catch (err) {
				nodes = [];
			}
			for (let i = 0; i < nodes.length; i++) {
				const match = getInlineHandlerMatch(nodes[i], /Game\.SelectDragonAura\((\d+)\)/);
				if (!match) continue;
				if (parseInt(match[1], 10) !== Number(slot)) continue;
				return getRect(nodes[i]);
			}
			return null;
		};

		const getDragonAuraPromptData = () => {
			const infoEl = document.getElementById("dragonAuraInfo");
			if (!infoEl) {
				return {
					open: false,
				};
			}
			const promptRoot = getClosestPromptRoot(infoEl) || document;
			const choices = [];
			let nodes = [];
			try {
				nodes = Array.from(promptRoot.querySelectorAll(".crate.enabled,.crate"));
			} catch (err) {
				nodes = [];
			}
			let promptSlot = null;
			for (let i = 0; i < nodes.length; i++) {
				const match = getInlineHandlerMatch(nodes[i], /Game\.SetDragonAura\((\d+),(\d+)\)/);
				if (!match) continue;
				const auraId = parseInt(match[1], 10);
				const slot = parseInt(match[2], 10);
				if (!Number.isFinite(auraId) || !Number.isFinite(slot)) continue;
				if (promptSlot === null) promptSlot = slot;
				choices.push({
					id: auraId,
					slot: slot,
					name:
						Game.dragonAuras && Game.dragonAuras[auraId]
							? stripHtml(Game.dragonAuras[auraId].dname || Game.dragonAuras[auraId].name)
							: null,
					target: getRect(nodes[i]),
				});
			}
			const confirmButton = document.getElementById("promptOption0");
			return {
				open: true,
				slot: promptSlot,
				selectedAuraId:
					typeof Game.SelectingDragonAura === "number" ? Game.SelectingDragonAura : null,
				currentAuraId:
					promptSlot === 1
						? typeof Game.dragonAura2 === "number"
							? Game.dragonAura2
							: null
						: typeof Game.dragonAura === "number"
							? Game.dragonAura
							: null,
				confirmTarget: getRect(confirmButton),
				choices: choices,
			};
		};

		const getDragonData = () => {
			if (!Game || !Array.isArray(Game.dragonLevels)) return null;
			const unlocked =
				(Game.Has && Game.Has("A crumbly egg")) ||
				(Array.isArray(Game.specialTabs) && Game.specialTabs.indexOf("dragon") >= 0);
			const dragonLevel = typeof Game.dragonLevel === "number" ? Game.dragonLevel : 0;
			const maxLevel = Game.dragonLevels.length - 1;
			const currentLevel = Game.dragonLevels[dragonLevel] || null;
			const nextLevel = dragonLevel < maxLevel ? Game.dragonLevels[dragonLevel] : null;
			const open = Game.specialTab === "dragon";
			const actionButton = open
				? getRect(
					findFirstElement([
						"#specialPopup .optionBox a.option.framed.large.title",
						"#specialPopup .optionBox .option.framed.large.title",
						"#specialPopup .optionBox a.option",
						"#specialPopup .optionBox .option",
					])
				)
				: null;
			const closeButton = open ? getRect(findFirstElement(["#specialPopup .close"])) : null;
			const nextCostAffordable =
				nextLevel && typeof nextLevel.cost === "function" ? !!nextLevel.cost() : false;
			const nextCostType =
				dragonLevel <= 4
					? "cookies"
					: dragonLevel < maxLevel - 2
						? "building_sacrifice"
						: "special";
			const nextRequiredBuilding =
				nextCostType === "building_sacrifice" && Array.isArray(Game.ObjectsById)
					? Game.ObjectsById[dragonLevel - 5] || null
					: null;
			const nextRequiredBuildingOwned =
				nextRequiredBuilding && typeof nextRequiredBuilding.amount === "number"
					? nextRequiredBuilding.amount
					: null;
			const nextRequiredBuildingAmount = nextRequiredBuilding ? 100 : null;
			const hasRequiredBuildingFloor =
				nextCostType !== "building_sacrifice"
					? true
					: typeof nextRequiredBuildingOwned === "number" &&
					  typeof nextRequiredBuildingAmount === "number" &&
					  nextRequiredBuildingOwned >= nextRequiredBuildingAmount;
			let highestOwnedBuilding = null;
			if (Array.isArray(Game.ObjectsById)) {
				for (let i = Game.ObjectsById.length - 1; i >= 0; i--) {
					const building = Game.ObjectsById[i];
					if (building && typeof building.amount === "number" && building.amount > 0) {
						highestOwnedBuilding = building;
						break;
					}
				}
			}
			const auraPrompt = getDragonAuraPromptData();

			return {
				unlocked: !!unlocked,
				open: open,
				level: dragonLevel,
				maxLevel: maxLevel,
				currentName: currentLevel ? stripHtml(currentLevel.name) : null,
				nextAction: nextLevel ? stripHtml(nextLevel.action) : null,
				nextCostAffordable: !!nextCostAffordable && hasRequiredBuildingFloor,
				nextCostText:
					nextLevel && typeof nextLevel.costStr === "function"
						? stripHtml(nextLevel.costStr())
						: null,
				nextCostType: nextCostType,
				nextCookieOnly: dragonLevel <= 4,
				nextRequiredBuildingId:
					nextRequiredBuilding && typeof nextRequiredBuilding.id === "number"
						? nextRequiredBuilding.id
						: null,
				nextRequiredBuildingName: nextRequiredBuilding ? stripHtml(nextRequiredBuilding.name) : null,
				nextRequiredBuildingAmount: nextRequiredBuildingAmount,
				nextRequiredBuildingOwned: nextRequiredBuildingOwned,
				dragonTab: getSpecialTabRect("dragon"),
				actionButton: actionButton,
				closeButton: closeButton,
				auraPrimary:
					Game.dragonAuras && Game.dragonAuras[Game.dragonAura]
						? stripHtml(Game.dragonAuras[Game.dragonAura].dname || Game.dragonAuras[Game.dragonAura].name)
						: null,
				auraPrimaryId: typeof Game.dragonAura === "number" ? Game.dragonAura : null,
				auraSecondary:
					Game.dragonAuras && Game.dragonAuras[Game.dragonAura2]
						? stripHtml(Game.dragonAuras[Game.dragonAura2].dname || Game.dragonAuras[Game.dragonAura2].name)
						: null,
				auraSecondaryId: typeof Game.dragonAura2 === "number" ? Game.dragonAura2 : null,
				auraPrimaryControl: open ? getDragonAuraSlotControl(0) : null,
				auraSecondaryControl: open ? getDragonAuraSlotControl(1) : null,
				auraPromptOpen: !!auraPrompt.open,
				auraPromptSlot: auraPrompt.slot,
				auraPromptSelectedAuraId: auraPrompt.selectedAuraId,
				auraPromptCurrentAuraId: auraPrompt.currentAuraId,
				auraPromptConfirm: auraPrompt.confirmTarget,
				auraPromptChoices: auraPrompt.choices,
				auraSwapCostFree: highestOwnedBuilding === null,
				auraSwapCostBuildingId:
					highestOwnedBuilding && typeof highestOwnedBuilding.id === "number"
						? highestOwnedBuilding.id
						: null,
				auraSwapCostBuildingName:
					highestOwnedBuilding ? stripHtml(highestOwnedBuilding.name) : null,
				auraSwapCostBuildingAmount:
					highestOwnedBuilding && typeof highestOwnedBuilding.amount === "number"
						? highestOwnedBuilding.amount
						: null,
			};
		};

		const getSantaData = () => {
			if (!Game || !Array.isArray(Game.santaLevels)) return null;
			const santaLevel = typeof Game.santaLevel === "number" ? Game.santaLevel : 0;
			const maxLevel = typeof Game.santaMax === "number" ? Game.santaMax : Game.santaLevels.length - 1;
			const currentLevel = Game.santaLevels[santaLevel] || null;
			const nextLevel = santaLevel < maxLevel ? Game.santaLevels[santaLevel + 1] : null;
			const open = Game.specialTab === "santa";
			const nextCost = santaLevel < maxLevel ? Math.pow(santaLevel + 1, santaLevel + 1) : null;
			const cookies = typeof Game.cookies === "number" ? Game.cookies : null;
			const canEvolve = cookies !== null && nextCost !== null ? cookies > nextCost : false;
			const clickTarget = getRect(findFirstElement(["#santaClick"])) || getSpecialTabRect("santa");
			const selectTarget = getRect(findFirstElement(["#santaLevel"]));
			let evolveTarget = null;
			if (open) {
				let nodes = [];
				try {
					nodes = Array.from(
						document.querySelectorAll(
							"#specialPopup .optionBox a.option.framed.large.title,#specialPopup .optionBox a.option"
						)
					);
				} catch (err) {
					nodes = [];
				}
				for (let i = 0; i < nodes.length; i++) {
					if (getInlineHandlerMatch(nodes[i], /Game\.UpgradeSanta\(\)/)) {
						evolveTarget = getRect(nodes[i]);
						break;
					}
				}
			}
			return {
				unlocked: !!(Game.Has && Game.Has("A festive hat")),
				open: open,
				level: santaLevel,
				maxLevel: maxLevel,
				currentName: currentLevel,
				nextName: nextLevel,
				nextCost: nextCost,
				cookies: cookies,
				canEvolve: canEvolve,
				clickTarget: clickTarget,
				selectTarget: selectTarget,
				evolveTarget: evolveTarget,
			};
		};

		const getStoreData = () => {
			return {
				buyMode: typeof Game.buyMode === "number" ? Game.buyMode : null,
				buyBulk: typeof Game.buyBulk === "number" ? Game.buyBulk : null,
				modeBuy: getRectBySelectors(["#storeBulkBuy"]),
				modeSell: getRectBySelectors(["#storeBulkSell"]),
				bulk1: getRectBySelectors(["#storeBulk1"]),
				bulk10: getRectBySelectors(["#storeBulk10"]),
				bulk100: getRectBySelectors(["#storeBulk100"]),
				bulkMax: getRectBySelectors(["#storeBulkMax"]),
				buyAllButton: getRectBySelectors(["#storeBuyAllButton"]),
				productsViewport: getProductsViewport(),
				sections: {
					products: {
						toggle: null,
						collapsed: false,
						visible: true,
					},
					upgrades: getStoreSection({
						contentSelectors: [
							"#upgrades",
							"#store #upgrades",
						],
						toggleSelectors: [
							"#upgradesTitle",
							"#upgradesHeader",
							"#upgradesToggle",
						],
						labelSelectors: [
							"#sectionLeft .title",
							"#sectionLeft .subsection",
							"#sectionLeft div",
						],
						labelPattern: /^upgrades$/i,
					}),
					switches: getStoreSection({
						contentSelectors: [
							"#toggleUpgrades",
							"#store #toggleUpgrades",
						],
						toggleSelectors: [
							"#toggleUpgradesTitle",
							"#toggleUpgradesHeader",
							"#toggleUpgradesToggle",
						],
						labelSelectors: [
							"#sectionLeft .title",
							"#sectionLeft .subsection",
							"#sectionLeft div",
						],
						labelPattern: /^switches$/i,
					}),
				},
			};
		};

		const getGoldenCookieData = () => {
			if (!Game || !Game.shimmerTypes || !Game.shimmerTypes["golden"]) return null;
			const golden = Game.shimmerTypes["golden"];
			return {
				time: typeof golden.time === "number" ? golden.time : null,
				minTime: typeof golden.minTime === "number" ? golden.minTime : null,
				maxTime: typeof golden.maxTime === "number" ? golden.maxTime : null,
				onScreen: typeof golden.n === "number" ? golden.n : 0,
				last: typeof golden.last === "number" ? golden.last : null,
			};
		};

		const getFarmOpenControl = (farm) => {
			const id = farm && typeof farm.id === "number" ? farm.id : null;
			let selectors = [
				"#gardenMinigameButton",
				"#farmMinigameButton",
				"[data-minigame='garden']",
				"[data-minigame='Garden']",
			];
			if (id !== null) {
				selectors = ["#productMinigameButton" + id].concat(selectors, [
					"#rowSpecial" + id,
					"#specialButton" + id,
					"#specialPopupButton" + id,
				]);
			}
			return getRectBySelectors(selectors);
		};

		const getTempleOpenControl = (temple) => {
			const id = temple && typeof temple.id === "number" ? temple.id : null;
			let selectors = [
				"#templeMinigameButton",
				"#pantheonButton",
				"[data-minigame='temple']",
				"[data-minigame='Temple']",
				"[data-minigame='pantheon']",
				"[data-minigame='Pantheon']",
			];
			if (id !== null) {
				selectors = ["#productMinigameButton" + id].concat(selectors, [
					"#rowSpecial" + id,
					"#specialButton" + id,
					"#specialPopupButton" + id,
				]);
			}
			return getRectBySelectors(selectors);
		};

		const getGardenData = () => {
			if (!Game || !Game.Objects || !Game.Objects["Farm"]) return null;
			const farm = Game.Objects["Farm"];
			const minigame = farm.minigame;
			const onMinigame = !!farm.onMinigame;
			if (!minigame || !Array.isArray(minigame.plot)) {
				return {
					onMinigame: onMinigame,
					openControl: getFarmOpenControl(farm),
					farmLevel: typeof farm.level === "number" ? farm.level : 0,
					farmAmount: typeof farm.amount === "number" ? farm.amount : 0,
				};
			}

			const currentSoil =
				typeof minigame.soil === "number" && Array.isArray(minigame.soilsById)
					? minigame.soilsById[minigame.soil] || null
					: null;
			const unlockedTiles = [];
			const plot = [];
			let occupiedTiles = 0;
			let maturePlants = 0;
			for (let y = 0; y < 6; y++) {
				for (let x = 0; x < 6; x++) {
					const unlocked = !!(minigame.isTileUnlocked && minigame.isTileUnlocked(x, y));
					const tile = Array.isArray(minigame.plot[y]) ? minigame.plot[y][x] : null;
					const plant = tile && tile[0] > 0 && Array.isArray(minigame.plantsById) ? minigame.plantsById[tile[0] - 1] : null;
					const age = tile && typeof tile[1] === "number" ? tile[1] : 0;
					const isMature = !!(plant && typeof plant.mature === "number" && age >= plant.mature);
					const isDying = !!(
						plant &&
						!plant.immortal &&
						typeof plant.ageTick === "number" &&
						typeof plant.ageTickR === "number" &&
						(age + Math.ceil(plant.ageTick + plant.ageTickR)) >= 100
					);
					if (unlocked) unlockedTiles.push({ x: x, y: y });
					if (plant) occupiedTiles++;
					if (isMature) maturePlants++;
					plot.push({
						x: x,
						y: y,
						unlocked: unlocked,
						target: onMinigame ? getRect(document.getElementById("gardenTile-" + x + "-" + y)) : null,
						plantId: plant ? plant.id : null,
						plantKey: plant ? plant.key : null,
						plantName: plant ? plant.name || plant.key : null,
						age: age,
						matureAge: plant && typeof plant.mature === "number" ? plant.mature : null,
						isMature: isMature,
						isDying: isDying,
						immortal: !!(plant && plant.immortal),
					});
				}
			}

			let plotMinX = null;
			let plotMinY = null;
			let plotMaxX = null;
			let plotMaxY = null;
			for (let i = 0; i < unlockedTiles.length; i++) {
				const tile = unlockedTiles[i];
				plotMinX = plotMinX === null ? tile.x : Math.min(plotMinX, tile.x);
				plotMinY = plotMinY === null ? tile.y : Math.min(plotMinY, tile.y);
				plotMaxX = plotMaxX === null ? tile.x : Math.max(plotMaxX, tile.x);
				plotMaxY = plotMaxY === null ? tile.y : Math.max(plotMaxY, tile.y);
			}

			const seeds = Array.isArray(minigame.plantsById)
				? minigame.plantsById.map((plant) => ({
						id: typeof plant.id === "number" ? plant.id : null,
						key: plant.key || null,
						name: plant.name || plant.key || null,
						unlocked: !!plant.unlocked,
						plantable: plant.plantable !== false,
						immortal: !!plant.immortal,
						weed: !!plant.weed,
						fungus: !!plant.fungus,
						matureAge: typeof plant.mature === "number" ? plant.mature : null,
						cost: typeof minigame.getCost === "function" ? minigame.getCost(plant) : null,
						selected: typeof minigame.seedSelected === "number" && plant.id === minigame.seedSelected,
						target: onMinigame ? getRect(document.getElementById("gardenSeed-" + plant.id)) : null,
				  }))
				: [];

			const soils = Array.isArray(minigame.soilsById)
				? minigame.soilsById.map((soil) => ({
						id: typeof soil.id === "number" ? soil.id : null,
						key: soil.key || null,
						name: soil.name || soil.key || null,
						tickMinutes: typeof soil.tick === "number" ? soil.tick : null,
						effMult: typeof soil.effMult === "number" ? soil.effMult : null,
						weedMult: typeof soil.weedMult === "number" ? soil.weedMult : null,
						req: typeof soil.req === "number" ? soil.req : null,
						selected: typeof minigame.soil === "number" && soil.id === minigame.soil,
						available: typeof farm.amount === "number" && typeof soil.req === "number" ? farm.amount >= soil.req : null,
						target: onMinigame ? getRect(document.getElementById("gardenSoil-" + soil.id)) : null,
				  }))
				: [];

			const toolMap = {};
			if (minigame.tools) {
				for (const key in minigame.tools) {
					if (!Object.prototype.hasOwnProperty.call(minigame.tools, key)) continue;
					const tool = minigame.tools[key];
					if (!tool || typeof tool.id !== "number") continue;
					toolMap[key] = {
						id: tool.id,
						name: tool.name || key,
						isOn: typeof tool.isOn === "function" ? !!tool.isOn() : false,
						displayed: typeof tool.isDisplayed === "function" ? !!tool.isDisplayed() : true,
						target: onMinigame ? getRect(document.getElementById("gardenTool-" + tool.id)) : null,
					};
				}
			}

			return {
				onMinigame: onMinigame,
				openControl: getFarmOpenControl(farm),
				farmLevel: typeof farm.level === "number" ? farm.level : 0,
				farmAmount: typeof farm.amount === "number" ? farm.amount : 0,
				soil: currentSoil
					? {
							id: typeof currentSoil.id === "number" ? currentSoil.id : null,
							key: currentSoil.key || null,
							name: currentSoil.name || currentSoil.key || null,
							tickMinutes: typeof currentSoil.tick === "number" ? currentSoil.tick : null,
					  }
					: null,
				soils: soils,
				seedSelected: typeof minigame.seedSelected === "number" ? minigame.seedSelected : null,
				seeds: seeds,
				plot: plot,
				plotTileCount: unlockedTiles.length,
				plotOccupied: occupiedTiles,
				plotMature: maturePlants,
				plotWidth:
					plotMinX === null || plotMaxX === null ? 0 : (plotMaxX - plotMinX + 1),
				plotHeight:
					plotMinY === null || plotMaxY === null ? 0 : (plotMaxY - plotMinY + 1),
				nextSoilAt: typeof minigame.nextSoil === "number" ? minigame.nextSoil : null,
				nextStepAt: typeof minigame.nextStep === "number" ? minigame.nextStep : null,
				freeze: !!minigame.freeze,
				tools: toolMap,
				plantsUnlocked: typeof minigame.plantsUnlockedN === "number" ? minigame.plantsUnlockedN : null,
				plantsTotal: typeof minigame.plantsN === "number" ? minigame.plantsN : null,
			};
		};

		const getTempleData = () => {
			if (!Game || !Game.Objects || !Game.Objects["Temple"]) return null;
			const temple = Game.Objects["Temple"];
			const minigame = temple.minigame;
			if (!minigame || !Array.isArray(minigame.slot)) {
				return {
					onMinigame: !!temple.onMinigame,
					openControl: getTempleOpenControl(temple),
					ruinLevel: Game.hasGod ? Game.hasGod("ruin") || 0 : 0,
				};
			}
			return {
				onMinigame: !!temple.onMinigame,
				openControl: getTempleOpenControl(temple),
				ruinLevel: Game.hasGod ? Game.hasGod("ruin") || 0 : 0,
				slots: minigame.slot.slice(0, 3),
				swaps: typeof minigame.swaps === "number" ? minigame.swaps : null,
			};
		};

		const getWrinklerData = () => {
			if (!Game || !Array.isArray(Game.wrinklers) || typeof Game.getWrinklersMax !== "function") return null;
			const canvasRect = getRect(document.getElementById("backgroundLeftCanvas"));
			const wrinklers = Game.wrinklers
				.filter((me) => me && typeof me.id === "number")
				.map((me) => ({
					id: me.id,
					phase: typeof me.phase === "number" ? me.phase : 0,
					close: typeof me.close === "number" ? me.close : 0,
					sucked: typeof me.sucked === "number" ? me.sucked : 0,
					hp: typeof me.hp === "number" ? me.hp : null,
					type: typeof me.type === "number" ? me.type : 0,
					clicks: typeof me.clicks === "number" ? me.clicks : 0,
					x: typeof me.x === "number" ? me.x : null,
					y: typeof me.y === "number" ? me.y : null,
					clientX:
						canvasRect && typeof me.x === "number" ? Math.round(canvasRect.left + me.x) : null,
					clientY:
						canvasRect && typeof me.y === "number" ? Math.round(canvasRect.top + me.y) : null,
					estimatedReward:
						typeof me.sucked === "number" ? me.sucked * getWrinklerRewardMultiplier(me) : 0,
				}));
			const active = wrinklers.filter((me) => me.phase > 0);
			const attached = wrinklers.filter((me) => me.phase === 2);
			const shiny = active.filter((me) => me.type === 1);
			return {
				elderWrath: typeof Game.elderWrath === "number" ? Game.elderWrath : 0,
				max: Game.getWrinklersMax(),
				total: wrinklers.length,
				active: active.length,
				attached: attached.length,
				shiny: shiny.length,
				suckedTotal: wrinklers.reduce((sum, me) => sum + (typeof me.sucked === "number" ? me.sucked : 0), 0),
				openSlots: Math.max(0, Game.getWrinklersMax() - active.length),
				wrinklers: wrinklers,
			};
		};

		const getNotesData = () => {
			let noteNodes = [];
			try {
				noteNodes = Array.from(document.querySelectorAll(".note"));
			} catch (err) {
				noteNodes = [];
			}
			const notes = noteNodes
				.map((node) => {
					if (!node) return null;
					const rect = getRect(node);
					if (!rect) return null;
					const closeEl = node.querySelector(".close");
					const closeRect = getRect(closeEl);
					if (!closeRect) return null;
					const titleEl = node.querySelector("h3");
					const title = (titleEl && titleEl.textContent ? titleEl.textContent : "").trim();
					const descEl = node.querySelector("h5");
					const desc = (descEl && descEl.textContent ? descEl.textContent : "").trim();
					return {
						id: typeof node.id === "string" && /^note-\d+$/.test(node.id) ? parseInt(node.id.slice(5), 10) : null,
						title: title,
						desc: desc,
						rect: rect,
						close: closeRect,
					};
				})
				.filter(Boolean);
			const closeAllEl = findFirstElement([".close.sidenote"]);
			return {
				count: notes.length,
				notes: notes,
				closeAll: getRect(closeAllEl),
			};
		};

		const writeSnapshot = () => {
			if (!Game || !Game.shimmers || !Game.bounds || !window.api || !window.api.send) return;
			const now = Date.now();
			if (now - lastWrite < WRITE_INTERVAL_MS) return;
			const profileStarted = performance.now();
			let upgradesMs = 0;
			let spellbookMs = 0;
			let bankMs = 0;
			let buildingsMs = 0;
			let gardenMs = 0;
			if (now - cacheTimestamp >= HEAVY_SECTION_CACHE_MS || !cachedStore) {
				const upgradesStarted = performance.now();
				cachedUpgrades = getUpgradesData();
				cachedBestUpgrade = getBestUpgrade(cachedUpgrades);
				upgradesMs = performance.now() - upgradesStarted;
				const spellbookStarted = performance.now();
				cachedSpellbook = getSpellbookData();
				spellbookMs = performance.now() - spellbookStarted;
				const bankStarted = performance.now();
				cachedBank = getBankData();
				bankMs = performance.now() - bankStarted;
				const buildingsStarted = performance.now();
				cachedBuildings = getBuildingsData();
				buildingsMs = performance.now() - buildingsStarted;
				const gardenStarted = performance.now();
				cachedGarden = getGardenData();
				gardenMs = performance.now() - gardenStarted;
				cachedStore = getStoreData();
				cacheTimestamp = now;
			}
			const wrinklersStarted = performance.now();
			const wrinklers = getWrinklerData();
			const wrinklersMs = performance.now() - wrinklersStarted;

			const payload = {
				timestamp: now,
				cookies: typeof Game.cookies === "number" ? Game.cookies : null,
				cookiesPs: typeof Game.cookiesPs === "number" ? Game.cookiesPs : null,
				cookiesPsRawHighest: typeof Game.cookiesPsRawHighest === "number" ? Game.cookiesPsRawHighest : null,
				globalCpsMult: typeof Game.globalCpsMult === "number" ? Game.globalCpsMult : null,
				milkProgress: typeof Game.milkProgress === "number" ? Game.milkProgress : null,
				computedMouseCps: typeof Game.computedMouseCps === "number" ? Game.computedMouseCps : null,
				season: typeof Game.season === "string" ? Game.season : null,
				seed: typeof Game.seed === "string" ? Game.seed : null,
				storeBuyMode: typeof Game.buyMode === "number" ? Game.buyMode : null,
				store: cachedStore,
				garden: cachedGarden,
				temple: getTempleData(),
				bounds: {
					left: Game.bounds.left,
					top: Game.bounds.top,
					right: Game.bounds.right,
					bottom: Game.bounds.bottom,
				},
				viewport: {
					width: window.innerWidth,
					height: window.innerHeight,
					devicePixelRatio: window.devicePixelRatio || 1,
				},
				bigCookie: getBigCookie(),
				spellbook: cachedSpellbook,
				wrinklers: wrinklers,
				lump: getLumpData(),
				notes: getNotesData(),
				dragon: getDragonData(),
				santa: getSantaData(),
				ascension: getAscensionData(),
				goldenCookie: getGoldenCookieData(),
				buffs: getActiveBuffs(),
				bank: cachedBank,
				buildings: cachedBuildings,
				upgrades: cachedUpgrades,
				bestUpgrade: cachedBestUpgrade,
				shimmers: serializeShimmers(),
				fortune: getFortuneData(),
				shimmerTelemetry: {
					predictorMode: WRATH_GATE_ENABLED ? "intercept_gate" : "observed_click_trace",
					preClickDeterministic: false,
					lastGoldenDecision: lastGoldenDecision,
					recentGoldenDecisions: goldenDecisionLog.slice(-10),
					blockedCount: blockedGoldenDecisions,
					lastChoice: lastGoldenDecision ? lastGoldenDecision.choice : null,
					lastAppliedChoice: lastGoldenDecision ? lastGoldenDecision.appliedChoice : null,
					lastGateClassification: lastGoldenDecision ? lastGoldenDecision.gateClassification : null,
					lastAllowed: lastGoldenDecision ? !lastGoldenDecision.blocked : null,
				},
			};
			payload.spell = getPreferredSpell(payload.spellbook);
			payload.profile = {
				totalMs: performance.now() - profileStarted,
				upgradesMs: upgradesMs,
				spellbookMs: spellbookMs,
				bankMs: bankMs,
				buildingsMs: buildingsMs,
				gardenMs: gardenMs,
				wrinklersMs: wrinklersMs,
			};

			const serialized = JSON.stringify(payload);

			if (serialized === lastPayload && now - lastWrite < STALE_WRITE_MS) return;

			let list = [["shimmers", serialized]];
			if (payload.shimmers.length > 0)
			{
				lastNonEmptyPayload = serialized;
				list.push(["shimmers_last", serialized]);
			}
			else if (lastNonEmptyPayload)
			{
				list.push(["shimmers_last", lastNonEmptyPayload]);
			}

			window.api.send("toMain", {
				id: "log to file",
				list: list,
			});
			lastPayload = serialized;
			lastWrite = now;
		};

		installGoldenDecisionHook();
		Game.registerHook("logic", writeSnapshot);
		writeSnapshot();
	},
});
