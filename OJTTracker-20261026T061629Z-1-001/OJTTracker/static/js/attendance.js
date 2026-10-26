document.addEventListener("DOMContentLoaded", () => {
  const message = document.getElementById("attendanceMessage");
  const buttons = [...document.querySelectorAll("[data-action]")];
  let location = null;
  document.addEventListener("ojttrack:location", event => { location = event.detail; });
  function show(text, kind) {
    if (!message) return;
    message.textContent = text;
    message.className = `form-message ${kind || ""}`;
  }
  async function submit(action, coords) {
    if (!coords) { show("Please retrieve your current GPS location first.", "error"); return; }
    const button = buttons.find(b => b.dataset.action === action);
    if (button) { button.disabled = true; button.textContent = "Submitting…"; }
    try {
      const response = await fetch("/attendance/action", {
        method: "POST",
        headers: {"Content-Type":"application/json", "X-Requested-With":"fetch"},
        body: JSON.stringify({...coords, action})
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || "Attendance could not be recorded.");
      show(result.message + (result.hours !== undefined ? ` Recorded duration: ${result.hours} hours.` : ""), "success");
      setTimeout(() => window.location.reload(), 1200);
    } catch (error) {
      show(error.message || "An unexpected error occurred.", "error");
      if (button) button.disabled = false;
    } finally {
      if (button && !button.disabled) button.textContent = action === "time_in" ? "Time in →" : "Time out ↗";
    }
  }
  buttons.forEach(button => button.addEventListener("click", () => {
    if (!location) {
      show("Please click “Get my current location” before recording attendance.", "error");
      return;
    }
    submit(button.dataset.action, location);
  }));
});
