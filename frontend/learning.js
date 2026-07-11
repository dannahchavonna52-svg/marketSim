(() => {
  const STORAGE_KEY = "marketsim_learning_progress_v1";
  const lessons = Array.isArray(window.MarketSimLearningContent) ? window.MarketSimLearningContent : [];
  let activeLessonId = null;
  let latestAnswers = null;

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function emptyProgress() {
    return { completedLessons: [], quizResults: {}, lastLessonId: null, submittedAt: null };
  }

  function loadProgress() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (!parsed || !Array.isArray(parsed.completedLessons) || typeof parsed.quizResults !== "object" || parsed.quizResults === null) {
        throw new Error("invalid learning progress");
      }
      return {
        completedLessons: parsed.completedLessons.filter((id) => lessons.some((lesson) => lesson.id === id)),
        quizResults: parsed.quizResults,
        lastLessonId: lessons.some((lesson) => lesson.id === parsed.lastLessonId) ? parsed.lastLessonId : null,
        submittedAt: parsed.submittedAt || null,
      };
    } catch (error) {
      const progress = emptyProgress();
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch (storageError) { console.warn("学习进度暂时无法保存", storageError); }
      return progress;
    }
  }

  function saveProgress(progress) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
      return true;
    } catch (error) {
      learningToast("学习进度保存失败，请检查浏览器存储权限");
      return false;
    }
  }

  function learningToast(message) {
    if (typeof window.showToast === "function") window.showToast(message);
    else {
      const status = document.querySelector("#learningStatus");
      if (status) status.textContent = message;
    }
  }

  function lessonById(id) {
    return lessons.find((lesson) => lesson.id === id) || lessons[0] || null;
  }

  function lessonState(lesson, progress) {
    if (progress.completedLessons.includes(lesson.id)) return "已完成";
    if (progress.quizResults[lesson.id] || progress.lastLessonId === lesson.id) return "学习中";
    return "未开始";
  }

  function nextLesson(progress) {
    return lessons.find((lesson) => !progress.completedLessons.includes(lesson.id)) || lessons[lessons.length - 1] || null;
  }

  function setLearningScreen(screenId) {
    ["learningHome", "learningCatalog", "learningDetail"].forEach((id) => {
      document.querySelector(`#${id}`)?.classList.toggle("learning-screen-hidden", id !== screenId);
    });
    window.scrollTo?.({ top: 0, behavior: "smooth" });
  }

  function activateLearningShell() {
    try {
      if (typeof finalPageGroups !== "undefined") finalPageGroups.learning = ["learningShell"];
      if (typeof PAGE_GROUPS !== "undefined") PAGE_GROUPS.learning = ["learningShell"];
    } catch (error) {
      console.warn("学习页面导航注册失败", error);
    }
    if (typeof window.showPage === "function") window.showPage("learning");
    else {
      document.querySelectorAll("#appView > section").forEach((section) => section.classList.add("page-hidden"));
      document.querySelector("#learningShell")?.classList.remove("page-hidden");
    }
    document.querySelectorAll("#bottomNav button").forEach((button) => button.classList.toggle("active", button.dataset.page === "learning"));
    const backtestNav = document.querySelector('#bottomNav button[data-page="aiBacktest"]');
    if (backtestNav) backtestNav.textContent = "回测实验";
  }

  function renderHome() {
    const box = document.querySelector("#learningHome");
    if (!box) return;
    const progress = loadProgress();
    const next = nextLesson(progress);
    const completed = progress.completedLessons.length;
    const percent = lessons.length ? Math.round((completed / lessons.length) * 100) : 0;
    const last = progress.lastLessonId ? lessonById(progress.lastLessonId) : null;
    box.innerHTML = `
      <header class="learning-hero">
        <div>
          <span class="learning-eyebrow">MarketSim 基金零基础课堂</span>
          <h1>今天先学懂一个概念</h1>
          <p>短课程、真实基金案例、历史回测和模拟训练，帮助你建立自己的分析步骤。</p>
        </div>
        <div class="learning-progress-summary" aria-label="学习进度">
          <strong>${completed}<small> / ${lessons.length} 课</small></strong>
          <span>已完成 ${percent}%</span>
        </div>
      </header>
      <div class="learning-progress-bar" aria-label="已完成 ${percent}%"><span style="width:${percent}%"></span></div>
      <section class="learning-next">
        <div>
          <span>下一节推荐</span>
          <h2>${safe(next?.title || "六节课程已完成")}</h2>
          <p>${safe(next?.summary || "可以重新打开课程复习重点。")}</p>
        </div>
        <button class="primary-btn" type="button" data-learning-action="open-lesson" data-lesson-id="${safe(next?.id || lessons[0]?.id || "")}">${completed ? "继续学习" : "开始第一课"}</button>
      </section>
      <div class="learning-home-actions">
        <button class="secondary-btn" type="button" data-learning-action="catalog">查看全部 6 节课</button>
        <button class="learning-tool" type="button" data-learning-action="tool" data-page="funds"><strong>基金案例</strong><span>用真实基金逐项认识数据</span></button>
        <button class="learning-tool" type="button" data-learning-action="tool" data-page="aiBacktest"><strong>历史回测实验</strong><span>用过去的数据观察一套规则曾经如何表现</span></button>
        <button class="learning-tool" type="button" data-learning-action="tool" data-page="trade"><strong>模拟训练</strong><span>只用模拟资金练习记录和复盘</span></button>
      </div>
      <p class="learning-last">${last ? `最近学习：${safe(last.title)}${progress.submittedAt ? ` · 小测提交于 ${safe(new Date(progress.submittedAt).toLocaleString("zh-CN"))}` : ""}` : "还没有学习记录，从第一课开始即可。"}</p>
      <aside class="learning-risk"><strong>固定风险提示</strong><span>基金净值会波动，历史表现和历史回测都不代表未来收益。本平台只用于学习和模拟研究，不构成投资建议。</span></aside>
      <p id="learningStatus" class="sr-status" role="status"></p>
    `;
    setLearningScreen("learningHome");
  }

  function renderCatalog() {
    const box = document.querySelector("#learningCatalog");
    if (!box) return;
    const progress = loadProgress();
    box.innerHTML = `
      <div class="learning-page-head">
        <button class="ghost-btn" type="button" data-learning-action="home">返回学习首页</button>
        <div><span>课程列表</span><h1>基金零基础 6 课</h1><p>建议按顺序学习，每节约 5–8 分钟。</p></div>
      </div>
      <div class="learning-course-grid">
        ${lessons.map((lesson) => {
          const state = lessonState(lesson, progress);
          return `<article class="learning-course-card ${state === "已完成" ? "completed" : ""}">
            <div class="learning-course-meta"><span>第 ${lesson.order} 课</span><b>${state}</b></div>
            <h2>${safe(lesson.title)}</h2>
            <p>${safe(lesson.summary)}</p>
            <small>预计 ${lesson.durationMinutes} 分钟</small>
            <button class="secondary-btn" type="button" data-learning-action="open-lesson" data-lesson-id="${safe(lesson.id)}">${state === "未开始" ? "开始学习" : state === "已完成" ? "重新查看" : "继续学习"}</button>
          </article>`;
        }).join("")}
      </div>
    `;
    setLearningScreen("learningCatalog");
  }

  function renderQuiz(lesson, progress) {
    const previous = progress.quizResults[lesson.id];
    return `
      <section class="learning-quiz" aria-labelledby="learningQuizTitle">
        <div class="section-title"><h2 id="learningQuizTitle">两道小测</h2><span>提交后才能完成本课</span></div>
        ${lesson.quiz.map((question, questionIndex) => `
          <fieldset class="learning-question">
            <legend>${questionIndex + 1}. ${safe(question.question)}</legend>
            ${question.options.map((option, optionIndex) => `
              <label><input type="radio" name="${safe(question.id)}" value="${optionIndex}" /> <span>${safe(option)}</span></label>
            `).join("")}
            <div id="${safe(question.id)}-feedback" class="learning-answer ${previous ? "show" : ""}">${previous ? `<strong>正确答案：${safe(question.options[question.answerIndex])}</strong><p>${safe(question.explanation)}</p>` : ""}</div>
          </fieldset>
        `).join("")}
        <div class="learning-quiz-actions">
          <button class="primary-btn" type="button" data-learning-action="submit-quiz">提交两道题</button>
          <span id="learningQuizResult" role="status">${previous ? `上次得分：${previous.score} / ${previous.total}` : "尚未提交"}</span>
        </div>
      </section>
    `;
  }

  function renderDetail(lessonId) {
    const lesson = lessonById(lessonId);
    const box = document.querySelector("#learningDetail");
    if (!lesson || !box) return;
    activeLessonId = lesson.id;
    latestAnswers = null;
    const progress = loadProgress();
    progress.lastLessonId = lesson.id;
    saveProgress(progress);
    const completed = progress.completedLessons.includes(lesson.id);
    const quizSubmitted = Boolean(progress.quizResults[lesson.id]);
    const next = lessons.find((item) => item.order === lesson.order + 1);
    box.innerHTML = `
      <div class="learning-page-head">
        <button class="ghost-btn" type="button" data-learning-action="catalog">返回课程列表</button>
        <div><span>第 ${lesson.order} 课 · 预计 ${lesson.durationMinutes} 分钟</span><h1>${safe(lesson.title)}</h1><p>${safe(lesson.summary)}</p></div>
      </div>
      <p class="learning-lead">${safe(lesson.explanation)}</p>
      <div class="learning-article">
        ${lesson.sections.map((section) => `<section><h2>${safe(section.heading)}</h2><p>${safe(section.body)}</p></section>`).join("")}
        <aside class="learning-example"><strong>${safe(lesson.example.title)}</strong><p>${safe(lesson.example.body)}</p></aside>
        <aside class="learning-misconception"><strong>常见误区</strong><p>${safe(lesson.misconception)}</p></aside>
      </div>
      ${renderQuiz(lesson, progress)}
      <section class="learning-tool-entry">
        <div><strong>${safe(lesson.toolLink.label)}</strong><p>${safe(lesson.toolLink.description)}</p></div>
        <button class="secondary-btn" type="button" data-learning-action="tool" data-page="${safe(lesson.toolLink.page)}">打开工具</button>
      </section>
      <div class="learning-complete-actions">
        <button id="completeLessonBtn" class="primary-btn" type="button" data-learning-action="complete" ${quizSubmitted ? "" : "disabled"}>${completed ? "本课已完成" : "标记课程完成"}</button>
        ${completed ? `<button class="ghost-btn" type="button" data-learning-action="restart">重新学习本课</button>` : ""}
        ${next ? `<button class="secondary-btn" type="button" data-learning-action="open-lesson" data-lesson-id="${safe(next.id)}">进入下一课</button>` : `<button class="secondary-btn" type="button" data-learning-action="home">返回学习首页</button>`}
      </div>
      <p class="learning-disclaimer">历史表现不代表未来收益，仅供学习和模拟研究，不构成投资建议。</p>
    `;
    setLearningScreen("learningDetail");
  }

  function submitQuiz() {
    const lesson = lessonById(activeLessonId);
    if (!lesson) return;
    const answers = lesson.quiz.map((question) => {
      const checked = document.querySelector(`input[name="${question.id}"]:checked`);
      return checked ? Number(checked.value) : null;
    });
    if (answers.some((answer) => answer === null)) {
      document.querySelector("#learningQuizResult").textContent = "请先完成两道题，再提交答案。";
      return;
    }
    latestAnswers = answers;
    let score = 0;
    lesson.quiz.forEach((question, index) => {
      const correct = answers[index] === question.answerIndex;
      if (correct) score += 1;
      const feedback = document.querySelector(`#${question.id}-feedback`);
      if (feedback) {
        feedback.className = `learning-answer show ${correct ? "correct" : "incorrect"}`;
        feedback.innerHTML = `<strong>${correct ? "回答正确" : "回答错误"} · 正确答案：${safe(question.options[question.answerIndex])}</strong><p>${safe(question.explanation)}</p>`;
      }
    });
    const submittedAt = new Date().toISOString();
    const progress = loadProgress();
    progress.lastLessonId = lesson.id;
    progress.submittedAt = submittedAt;
    progress.quizResults[lesson.id] = { score, total: lesson.quiz.length, submittedAt };
    saveProgress(progress);
    document.querySelector("#learningQuizResult").textContent = `本次得分：${score} / ${lesson.quiz.length}。已显示每题答案解释。`;
    const completeButton = document.querySelector("#completeLessonBtn");
    if (completeButton) completeButton.disabled = false;
  }

  function completeLesson() {
    const lesson = lessonById(activeLessonId);
    const progress = loadProgress();
    if (!lesson || !progress.quizResults[lesson.id]) {
      learningToast("请先提交两道小测，再完成课程");
      return;
    }
    if (!progress.completedLessons.includes(lesson.id)) progress.completedLessons.push(lesson.id);
    progress.lastLessonId = lesson.id;
    saveProgress(progress);
    renderDetail(lesson.id);
    learningToast("课程已完成，学习进度已保存");
  }

  function restartLesson() {
    const lesson = lessonById(activeLessonId);
    if (!lesson) return;
    const progress = loadProgress();
    progress.completedLessons = progress.completedLessons.filter((id) => id !== lesson.id);
    delete progress.quizResults[lesson.id];
    progress.lastLessonId = lesson.id;
    progress.submittedAt = null;
    saveProgress(progress);
    renderDetail(lesson.id);
    learningToast("已重置本课，可以重新学习和答题");
  }

  function openTool(page) {
    if (typeof window.showPage === "function") window.showPage(page);
    else document.querySelector(`#bottomNav button[data-page="${page}"]`)?.click();
  }

  function showLearningHome() {
    activateLearningShell();
    renderHome();
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-learning-action]");
    if (!target) return;
    const action = target.dataset.learningAction;
    if (action === "home") showLearningHome();
    else if (action === "catalog") { activateLearningShell(); renderCatalog(); }
    else if (action === "open-lesson") { activateLearningShell(); renderDetail(target.dataset.lessonId); }
    else if (action === "submit-quiz") submitQuiz();
    else if (action === "complete") completeLesson();
    else if (action === "restart") restartLesson();
    else if (action === "tool") openTool(target.dataset.page);
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest('#bottomNav button[data-page="learning"]')) showLearningHome();
  });

  document.addEventListener("marketsim:login", () => setTimeout(showLearningHome, 0));

  const requestedLesson = new URLSearchParams(window.location.search).get("lesson");
  setTimeout(() => {
    if (!document.querySelector("#appView")?.classList.contains("hidden")) {
      activateLearningShell();
      if (requestedLesson && lessonById(requestedLesson)?.id === requestedLesson) renderDetail(requestedLesson);
      else renderHome();
    }
  }, 80);

  window.MarketSimLearning = { loadProgress, showLearningHome, renderCatalog, renderDetail };
})();
