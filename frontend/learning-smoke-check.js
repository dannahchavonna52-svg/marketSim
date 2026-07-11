const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const frontendDir = __dirname;
const windowMock = {};
vm.runInNewContext(
  fs.readFileSync(path.join(frontendDir, "learning-content.js"), "utf8"),
  { window: windowMock }
);

const lessons = windowMock.MarketSimLearningContent;
assert.ok(Array.isArray(lessons), "learning content must export an array");
assert.equal(lessons.length, 6, "phase one must contain exactly 6 lessons");
assert.equal(new Set(lessons.map((lesson) => lesson.id)).size, 6, "lesson IDs must be unique");

for (const lesson of lessons) {
  assert.ok(lesson.id && lesson.title && lesson.summary && lesson.explanation);
  assert.ok(Number.isInteger(lesson.durationMinutes) && lesson.durationMinutes > 0);
  assert.ok(Array.isArray(lesson.sections) && lesson.sections.length >= 3 && lesson.sections.length <= 5);
  assert.ok(lesson.sections.every((section) => section.heading && section.body.length >= 40));
  assert.ok(lesson.example?.title && lesson.example?.body);
  assert.ok(lesson.misconception);
  assert.equal(lesson.takeaways?.length, 3, `${lesson.id} must contain 3 takeaways`);
  assert.equal(lesson.quiz?.length, 2, `${lesson.id} must contain 2 questions`);
  for (const question of lesson.quiz) {
    assert.ok(question.id && question.question && question.explanation);
    assert.ok(Array.isArray(question.options) && question.options.length >= 2);
    assert.ok(Number.isInteger(question.answerIndex));
    assert.ok(question.answerIndex >= 0 && question.answerIndex < question.options.length);
  }
  assert.ok(["funds", "aiBacktest", "trade"].includes(lesson.toolLink?.page));
}

const indexHtml = fs.readFileSync(path.join(frontendDir, "index.html"), "utf8");
for (const id of ["learningShell", "learningHome", "learningCatalog", "learningDetail"]) {
  assert.ok(indexHtml.includes(`id="${id}"`), `index.html is missing #${id}`);
}
assert.ok(indexHtml.includes('data-page="learning"'));
assert.ok(indexHtml.includes("learning-content.js"));
assert.ok(indexHtml.includes("learning.js"));
assert.ok(indexHtml.includes("learning.css"));

const learningScript = fs.readFileSync(path.join(frontendDir, "learning.js"), "utf8");
assert.ok(learningScript.includes("marketsim_learning_progress_v1"));
assert.ok(learningScript.includes("JSON.parse"));
assert.ok(learningScript.includes("try {"));
assert.ok(!learningScript.includes("/api/ai-research/"), "default learning flow must not call AI research");

const storage = {
  value: "{broken-json",
  getItem() { return this.value; },
  setItem(key, value) { this.value = value; },
};
const learningWindow = {
  MarketSimLearningContent: lessons,
  location: { search: "" },
};
const learningDocument = {
  addEventListener() {},
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
vm.runInNewContext(learningScript, {
  window: learningWindow,
  document: learningDocument,
  localStorage: storage,
  console,
  URLSearchParams,
  setTimeout() {},
});
const recovered = learningWindow.MarketSimLearning.loadProgress();
assert.deepEqual(Array.from(recovered.completedLessons), []);
assert.equal(Object.keys(recovered.quizResults).length, 0);
assert.doesNotThrow(() => JSON.parse(storage.value));

console.log("Learning MVP smoke check passed (6 lessons, 12 questions, DOM and corrupt-storage recovery)");
