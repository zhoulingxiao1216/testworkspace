const toast = document.querySelector("[data-toast]");

function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-show"), 1800);
}

document.querySelectorAll("[data-dialog-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const dialog = document.querySelector(button.dataset.dialogTarget);
    if (dialog) dialog.classList.add("is-open");
  });
});

document.querySelectorAll("[data-dialog-close]").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest(".modal")?.classList.remove("is-open");
  });
});

document.querySelectorAll(".modal").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.classList.remove("is-open");
  });
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.copy} 已复制`));
});

document.querySelectorAll("[data-save]").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest(".modal")?.classList.remove("is-open");
    showToast(button.dataset.save);
  });
});

document.querySelectorAll("[data-action-toast]").forEach((button) => {
  button.addEventListener("click", () => showToast(button.dataset.actionToast));
});

document.querySelectorAll("[data-show-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(button.dataset.showTarget);
    target?.classList.remove("is-hidden");
  });
});

document.querySelectorAll("[data-hide-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(button.dataset.hideTarget);
    target?.classList.add("is-hidden");
  });
});

document.querySelectorAll("[data-stepper]").forEach((stepper) => {
  const input = stepper.querySelector("input");
  stepper.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = Number(button.dataset.step);
      const nextValue = Math.max(1, Number(input.value || 0) + direction);
      input.value = nextValue;
      showToast(`限流已调整为 ${nextValue} 次/分`);
    });
  });
});
