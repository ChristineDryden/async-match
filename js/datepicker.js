(function (root) {
  var WEEK = ["日", "一", "二", "三", "四", "五", "六"];

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function startOfDay(d) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function sameDay(a, b) {
    return (
      a &&
      b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  function formatValue(date) {
    if (!date) return "";
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes())
    );
  }

  function cloneDate(date) {
    return date ? new Date(date.getTime()) : null;
  }

  function buildCalendarDays(year, month) {
    var first = new Date(year, month, 1);
    var start = first.getDay();
    var days = [];
    var cursor = new Date(year, month, 1 - start);
    for (var i = 0; i < 42; i++) {
      days.push(new Date(cursor.getTime()));
      cursor.setDate(cursor.getDate() + 1);
    }
    return days;
  }

  function mount(host, options) {
    options = options || {};
    var placeholder = options.placeholder || "选择时间";
    var defaultHour = options.defaultHour == null ? 0 : options.defaultHour;
    var defaultMinute = options.defaultMinute == null ? 0 : options.defaultMinute;
    var value = null;
    var view = startOfDay(new Date());
    var draft = null;
    var open = false;

    host.classList.add("dp");
    host.innerHTML =
      '<button type="button" class="dp-trigger" aria-haspopup="dialog">' +
      '<span class="dp-text dp-placeholder"></span>' +
      '<span class="dp-icon" aria-hidden="true">' +
      '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8">' +
      '<rect x="3.5" y="5" width="17" height="15" rx="2"/>' +
      '<path d="M8 3.5v3M16 3.5v3M3.5 9.5h17"/>' +
      "</svg></span></button>" +
      '<div class="dp-panel" hidden></div>';

    var trigger = host.querySelector(".dp-trigger");
    var textEl = host.querySelector(".dp-text");
    var panel = host.querySelector(".dp-panel");

    function setLabel() {
      if (value) {
        textEl.textContent = formatValue(value);
        textEl.classList.remove("dp-placeholder");
      } else {
        textEl.textContent = placeholder;
        textEl.classList.add("dp-placeholder");
      }
    }

    function ensureDraft() {
      if (draft) return;
      if (value) {
        draft = cloneDate(value);
        return;
      }
      draft = new Date();
      draft.setHours(defaultHour, defaultMinute, 0, 0);
    }

    function close() {
      open = false;
      panel.hidden = true;
      trigger.classList.remove("open");
    }

    function render() {
      ensureDraft();
      var year = view.getFullYear();
      var month = view.getMonth();
      var days = buildCalendarDays(year, month);
      var today = new Date();
      var hour = draft.getHours();
      var minute = draft.getMinutes();

      var dayCells = days
        .map(function (day) {
          var classes = ["dp-day"];
          if (day.getMonth() !== month) classes.push("out");
          if (sameDay(day, today)) classes.push("today");
          if (sameDay(day, draft)) classes.push("selected");
          return (
            '<button type="button" class="' +
            classes.join(" ") +
            '" data-y="' +
            day.getFullYear() +
            '" data-m="' +
            day.getMonth() +
            '" data-d="' +
            day.getDate() +
            '">' +
            day.getDate() +
            "</button>"
          );
        })
        .join("");

      var hours = "";
      for (var h = 0; h < 24; h++) {
        hours +=
          '<button type="button" class="dp-time-item' +
          (h === hour ? " selected" : "") +
          '" data-hour="' +
          h +
          '">' +
          pad(h) +
          "</button>";
      }
      var minutes = "";
      for (var m = 0; m < 60; m++) {
        minutes +=
          '<button type="button" class="dp-time-item' +
          (m === minute ? " selected" : "") +
          '" data-minute="' +
          m +
          '">' +
          pad(m) +
          "</button>";
      }

      panel.innerHTML =
        '<div class="dp-calendar">' +
        '<div class="dp-head">' +
        '<button type="button" class="dp-nav" data-nav="prev-year" aria-label="上一年">«</button>' +
        '<button type="button" class="dp-nav" data-nav="prev-month" aria-label="上个月">‹</button>' +
        '<div class="dp-title">' +
        year +
        "年 " +
        (month + 1) +
        "月</div>" +
        '<button type="button" class="dp-nav" data-nav="next-month" aria-label="下个月">›</button>' +
        '<button type="button" class="dp-nav" data-nav="next-year" aria-label="下一年">»</button>' +
        "</div>" +
        '<div class="dp-weeks">' +
        WEEK.map(function (w) {
          return "<span>" + w + "</span>";
        }).join("") +
        "</div>" +
        '<div class="dp-grid">' +
        dayCells +
        "</div>" +
        "</div>" +
        '<div class="dp-time">' +
        '<div class="dp-time-col" data-col="hour">' +
        hours +
        "</div>" +
        '<div class="dp-time-col" data-col="minute">' +
        minutes +
        "</div>" +
        "</div>" +
        '<div class="dp-foot">' +
        '<button type="button" class="dp-now">此刻</button>' +
        '<button type="button" class="dp-ok">确定</button>' +
        "</div>";

      panel.querySelectorAll(".dp-time-col").forEach(function (col) {
        var selected = col.querySelector(".selected");
        if (selected) {
          col.scrollTop = Math.max(0, selected.offsetTop - 72);
        }
      });
    }

    function openPanel() {
      document.querySelectorAll(".dp-panel").forEach(function (el) {
        if (el !== panel) el.hidden = true;
      });
      document.querySelectorAll(".dp-trigger").forEach(function (el) {
        if (el !== trigger) el.classList.remove("open");
      });
      draft = cloneDate(value);
      view = startOfDay(value || new Date());
      open = true;
      panel.hidden = false;
      trigger.classList.add("open");
      render();
    }

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      if (open) close();
      else openPanel();
    });

    panel.addEventListener("click", function (event) {
      event.stopPropagation();
      var nav = event.target.closest("[data-nav]");
      if (nav) {
        var kind = nav.getAttribute("data-nav");
        if (kind === "prev-month") view.setMonth(view.getMonth() - 1);
        if (kind === "next-month") view.setMonth(view.getMonth() + 1);
        if (kind === "prev-year") view.setFullYear(view.getFullYear() - 1);
        if (kind === "next-year") view.setFullYear(view.getFullYear() + 1);
        render();
        return;
      }
      var dayBtn = event.target.closest(".dp-day");
      if (dayBtn) {
        ensureDraft();
        draft.setFullYear(
          Number(dayBtn.dataset.y),
          Number(dayBtn.dataset.m),
          Number(dayBtn.dataset.d)
        );
        view = startOfDay(draft);
        render();
        return;
      }
      var hourBtn = event.target.closest("[data-hour]");
      if (hourBtn) {
        ensureDraft();
        draft.setHours(Number(hourBtn.dataset.hour));
        render();
        return;
      }
      var minuteBtn = event.target.closest("[data-minute]");
      if (minuteBtn) {
        ensureDraft();
        draft.setMinutes(Number(minuteBtn.dataset.minute));
        render();
        return;
      }
      if (event.target.closest(".dp-now")) {
        draft = new Date();
        view = startOfDay(draft);
        render();
        return;
      }
      if (event.target.closest(".dp-ok")) {
        ensureDraft();
        value = cloneDate(draft);
        setLabel();
        close();
        if (options.onChange) options.onChange(cloneDate(value));
      }
    });

    document.addEventListener("click", function (event) {
      if (!open) return;
      if (!host.contains(event.target)) close();
    });

    setLabel();

    return {
      getValue: function () {
        return cloneDate(value);
      },
      setValue: function (next) {
        value = next ? new Date(next) : null;
        setLabel();
      },
      clear: function () {
        value = null;
        draft = null;
        setLabel();
        close();
      },
    };
  }

  root.DatePicker = { mount: mount, formatValue: formatValue };
})(typeof window !== "undefined" ? window : globalThis);
