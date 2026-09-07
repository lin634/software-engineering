/**
 * Flux Realism 图像生成器 - 前端逻辑
 * =================================
 * 负责与后端 /api/generate 接口交互，
 * 管理 UI 状态切换（空/加载/结果/错误）。
 */

// ============================================================
// 预设提示词模板
// ============================================================
const PRESETS = {
    portrait: {
        prompt: "A close-up portrait of an elderly fisherman with weathered, sun-darkened skin and deep wrinkles, piercing blue eyes, white beard, wearing a rain-soaked yellow raincoat, standing on a weathered wooden dock at dawn, soft overcast lighting, droplets of water on his skin, shot on Canon EOS R5 with 85mm f/1.4 lens, shallow depth of field, ultra realistic, highly detailed, 8K photography",
        negative: "cartoon, anime, illustration, painting, low quality, blurry, deformed, extra fingers, watermark, text, oversaturated",
    },
    landscape: {
        prompt: "A breathtaking mountain landscape at golden hour, snow-capped peaks reflecting warm sunlight, a crystal clear alpine lake in the foreground with perfect mirror reflection, scattered wildflowers in purple and yellow, dramatic clouds with god rays piercing through, shot on Sony A7R IV, 16-35mm wide-angle lens, f/11, tripod-mounted, ultra sharp, photorealistic, National Geographic style",
        negative: "cartoon, anime, illustration, painting, low quality, blurry, oversaturated, unnatural colors, text, watermark",
    },
    food: {
        prompt: "A gourmet burger on a rustic wooden board, juicy beef patty with grill marks, melted cheddar cheese dripping down the sides, fresh lettuce, tomato, and caramelized onions, sesame brioche bun, side of golden crispy fries, warm restaurant lighting, shot from 45-degree angle, Canon 100mm f/2.8 macro lens, shallow depth of field, food photography, ultra realistic, mouth-watering",
        negative: "cartoon, anime, illustration, low quality, blurry, unappetizing, plastic-looking, text, watermark",
    },
    street: {
        prompt: "A rainy evening street scene in Tokyo at night, neon signs reflecting on wet asphalt, a lone figure with an umbrella walking under glowing storefronts, steam rising from a ramen stall, bokeh lights in red blue and pink, shot on Leica Q2, 28mm f/1.7, ISO 3200, cinematic mood, ultra realistic street photography",
        negative: "cartoon, anime style, illustration, painting, low quality, blurry, daylight, text, watermark",
    },
};

// ============================================================
// DOM 元素引用
// ============================================================
const el = {
    statusBadge: document.getElementById("status-badge"),
    prompt: document.getElementById("prompt"),
    promptCount: document.getElementById("prompt-count"),
    negPrompt: document.getElementById("negative-prompt"),
    negCount: document.getElementById("neg-count"),
    width: document.getElementById("width"),
    height: document.getElementById("height"),
    steps: document.getElementById("steps"),
    stepsValue: document.getElementById("steps-value"),
    guidance: document.getElementById("guidance"),
    guidanceValue: document.getElementById("guidance-value"),
    seed: document.getElementById("seed"),
    randomSeedBtn: document.getElementById("random-seed"),
    generateBtn: document.getElementById("generate-btn"),
    btnText: document.querySelector(".btn-text"),
    btnLoading: document.querySelector(".btn-loading"),
    downloadBtn: document.getElementById("download-btn"),
    fullscreenBtn: document.getElementById("fullscreen-btn"),
    imageContainer: document.getElementById("image-container"),
    emptyState: document.getElementById("empty-state"),
    loadingState: document.getElementById("loading-state"),
    resultState: document.getElementById("result-state"),
    resultImage: document.getElementById("result-image"),
    errorState: document.getElementById("error-state"),
    errorMessage: document.getElementById("error-message"),
    resultInfo: document.getElementById("result-info"),
    paramsDisplay: document.getElementById("params-display"),
    // 模态框
    modalOverlay: document.getElementById("modal-overlay"),
    modalImage: document.getElementById("modal-image"),
    modalClose: document.getElementById("modal-close"),
};

// 存储当前生成的 Base64 图像（供下载使用）
let currentImageBase64 = "";

// ============================================================
// 工具函数
// ============================================================

/**
 * 更新字符计数
 */
function updateCharCount(textarea, counter, max) {
    counter.textContent = `${textarea.value.length} / ${max}`;
}

/**
 * 切换 UI 状态
 */
function showState(state) {
    el.emptyState.hidden = true;
    el.loadingState.hidden = true;
    el.resultState.hidden = true;
    el.errorState.hidden = true;

    switch (state) {
        case "empty":
            el.emptyState.hidden = false;
            break;
        case "loading":
            el.loadingState.hidden = false;
            break;
        case "result":
            el.resultState.hidden = false;
            break;
        case "error":
            el.errorState.hidden = false;
            break;
    }
}

/**
 * 设置按钮加载状态
 */
function setLoading(loading) {
    el.generateBtn.disabled = loading;
    el.btnText.hidden = loading;
    el.btnLoading.hidden = !loading;
}

/**
 * 健康检查 - 确认后端服务和 Token 配置状态
 */
async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();

        el.statusBadge.classList.remove("checking");

        if (data.token_configured) {
            el.statusBadge.textContent = `● 在线 | ${data.model}`;
            el.statusBadge.classList.add("online");
        } else {
            el.statusBadge.textContent = "⚠ Token 未配置";
            el.statusBadge.classList.add("offline");
        }
    } catch (err) {
        el.statusBadge.classList.remove("checking");
        el.statusBadge.textContent = "● 离线";
        el.statusBadge.classList.add("offline");
    }
}

// ============================================================
// 核心功能：生成图像
// ============================================================
async function generateImage() {
    const prompt = el.prompt.value.trim();
    if (!prompt) {
        el.prompt.focus();
        showState("error");
        el.errorMessage.textContent = "请输入提示词后再生成图像";
        return;
    }

    // 收集参数
    const requestBody = {
        prompt: prompt,
        negative_prompt: el.negPrompt.value.trim() || null,
        width: parseInt(el.width.value),
        height: parseInt(el.height.value),
        num_inference_steps: parseInt(el.steps.value),
        guidance_scale: parseFloat(el.guidance.value),
        seed: el.seed.value ? parseInt(el.seed.value) : null,
    };

    // 切换到加载状态
    showState("loading");
    setLoading(true);
    el.downloadBtn.disabled = true;
    el.fullscreenBtn.disabled = true;

    try {
        // 调用后端 API
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
        });

        const data = await response.json();

        if (data.success && data.image_base64) {
            // 成功：显示图像
            currentImageBase64 = data.image_base64;
            el.resultImage.src = `data:image/png;base64,${data.image_base64}`;
            showState("result");

            // 显示参数信息
            el.resultInfo.hidden = false;
            const params = data.parameters;
            el.paramsDisplay.innerHTML = Object.entries(params)
                .map(
                    ([key, value]) =>
                        `<div class="param-line"><span class="param-key">${key}:</span><span>${value}</span></div>`
                )
                .join("");

            // 启用下载和全屏按钮
            el.downloadBtn.disabled = false;
            el.fullscreenBtn.disabled = false;
        } else {
            // 失败：显示错误
            showState("error");
            el.errorMessage.textContent = data.message || "生成失败，请检查后端日志";
        }
    } catch (err) {
        showState("error");
        el.errorMessage.textContent = `网络错误: ${err.message}`;
    } finally {
        setLoading(false);
    }
}

/**
 * 下载当前生成的图像
 */
function downloadImage() {
    if (!currentImageBase64) return;

    const link = document.createElement("a");
    link.href = `data:image/png;base64,${currentImageBase64}`;
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    link.download = `flux-realism-${timestamp}.png`;
    link.click();
}

/**
 * 打开全屏查看模态框
 */
function openModal() {
    if (!currentImageBase64) return;
    el.modalImage.src = `data:image/png;base64,${currentImageBase64}`;
    el.modalOverlay.hidden = false;
}

/**
 * 关闭全屏模态框
 */
function closeModal() {
    el.modalOverlay.hidden = true;
}

// ============================================================
// 事件监听
// ============================================================

// 提示词字符计数
el.prompt.addEventListener("input", () => updateCharCount(el.prompt, el.promptCount, 2000));
el.negPrompt.addEventListener("input", () => updateCharCount(el.negPrompt, el.negCount, 1000));

// 滑块值实时显示
el.steps.addEventListener("input", () => {
    el.stepsValue.textContent = el.steps.value;
});

el.guidance.addEventListener("input", () => {
    el.guidanceValue.textContent = parseFloat(el.guidance.value).toFixed(1);
});

// 随机种子按钮
el.randomSeedBtn.addEventListener("click", () => {
    el.seed.value = Math.floor(Math.random() * 4294967295);
});

// 预设提示词按钮
document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const preset = PRESETS[btn.dataset.preset];
        if (preset) {
            el.prompt.value = preset.prompt;
            el.negPrompt.value = preset.negative;
            updateCharCount(el.prompt, el.promptCount, 2000);
            updateCharCount(el.negPrompt, el.negCount, 1000);
            el.prompt.focus();
        }
    });
});

// 生成按钮
el.generateBtn.addEventListener("click", generateImage);

// Ctrl+Enter 快捷生成
el.prompt.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        generateImage();
    }
});

// 下载和全屏按钮
el.downloadBtn.addEventListener("click", downloadImage);
el.fullscreenBtn.addEventListener("click", openModal);
el.modalClose.addEventListener("click", closeModal);
el.modalOverlay.addEventListener("click", (e) => {
    if (e.target === el.modalOverlay) closeModal();
});

// ESC 关闭模态框
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.modalOverlay.hidden) {
        closeModal();
    }
});

// ============================================================
// 初始化
// ============================================================
checkHealth();
updateCharCount(el.prompt, el.promptCount, 2000);
updateCharCount(el.negPrompt, el.negCount, 1000);
