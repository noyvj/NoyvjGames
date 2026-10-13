(function () {
  "use strict";
  var KEY = "dr-offline-charts";
  var MAX_SAVED = 5;

  function getSaved() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
  }

  function setSaved(arr) {
    try { localStorage.setItem(KEY, JSON.stringify(arr)); } catch (e) { /* quota exceeded */ }
  }

  window.DROffline = {
    save: function (chartId, chartName, state) {
      var list = getSaved();
      for (var i = list.length - 1; i >= 0; i--) {
        if (list[i].id === chartId) list.splice(i, 1);
      }
      list.unshift({ id: chartId, name: chartName, state: state, savedAt: Date.now() });
      if (list.length > MAX_SAVED) list.pop();
      setSaved(list);
    },

    loadList: function () { return getSaved(); },

    loadChart: function (index) {
      var list = getSaved();
      if (index >= 0 && index < list.length) {
        return list[index];
      }
      return null;
    },

    removeChart: function (index) {
      var list = getSaved();
      if (index >= 0 && index < list.length) {
        list.splice(index, 1);
        setSaved(list);
      }
    }
  };
})();
