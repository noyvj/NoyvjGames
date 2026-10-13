(function () {
  "use strict";

  var OIL_LOW = 3;
  var REPAIR_LOW = 3;

  function updateGlow(oil, repair) {
    var oilChip = document.querySelector('.chip[data-stat="oil"]');
    var repairChip = document.querySelector('.chip[data-stat="repair"]');
    if (!oilChip || !repairChip) return;

    if (oil < OIL_LOW) {
      oilChip.setAttribute('data-state', 'low');
    } else {
      oilChip.removeAttribute('data-state');
    }

    if (repair < REPAIR_LOW) {
      repairChip.setAttribute('data-state', 'low');
    } else {
      repairChip.removeAttribute('data-state');
    }
  }

  window.updateMobileHudGlow = updateGlow;
})();
