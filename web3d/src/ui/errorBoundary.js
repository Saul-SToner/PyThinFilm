export function showErrorModal(title, message) {
  const modal = document.querySelector("#error-boundary-modal");
  const titleEl = document.querySelector("#error-title");
  const msgEl = document.querySelector("#error-message");

  if (modal && titleEl && msgEl) {
    titleEl.textContent = title;
    msgEl.textContent = message;
    modal.classList.remove("hidden");
  }
}

export function hideErrorModal() {
  const modal = document.querySelector("#error-boundary-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

export function setupErrorBoundary() {
  const btnClose = document.querySelector("#btn-close-error");
  if (btnClose) {
    btnClose.addEventListener("click", () => {
      hideErrorModal();
    });
  }
}
