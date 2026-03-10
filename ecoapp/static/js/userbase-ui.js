document.addEventListener("DOMContentLoaded", function () {
  if (!window.bootstrap) {
    return;
  }

  if (window.bootstrap.Tooltip) {
    const tooltipTargets = document.querySelectorAll(
      '[data-bs-toggle="tooltip"], a[title], button[title]'
    );
    tooltipTargets.forEach(function (target) {
      if (!window.bootstrap.Tooltip.getInstance(target)) {
        new window.bootstrap.Tooltip(target);
      }
    });
  }

  if (window.bootstrap.Modal) {
    const reminderModalElement = document.getElementById("reminderModal");
    if (reminderModalElement) {
      const reminderModal = new window.bootstrap.Modal(reminderModalElement);
      reminderModal.show();
    }
  }
});
