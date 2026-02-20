/**
 * G11_SHEET_ALIAS.gs
 * Centralized sheet alias resolver (fix RISKS/RISQUES without patching every file).
 */

var IAPF_SHEETS = (function () {

  // Canonical keys used by code
  var MAP = {
    "MEMORY_LOG": ["MEMORY_LOG"],
    "SNAPSHOT_ACTIVE": ["SNAPSHOT_ACTIVE"],
    "CONFLITS_DETECTES": ["CONFLITS_DETECTES"],
    "DEPENDANCES_SCRIPTS": ["DEPENDANCES_SCRIPTS"],
    "CARTOGRAPHIE_APPELS": ["CARTOGRAPHIE_APPELS"],
    "REGLES_DE_GOUVERNANCE": ["REGLES_DE_GOUVERNANCE"],
    "RISKS": ["RISKS", "RISQUES"] // <— your issue fixed here
  };

  function resolveName_(key) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const names = MAP[String(key)] || [String(key)];
    for (var i = 0; i < names.length; i++) {
      const sh = ss.getSheetByName(names[i]);
      if (sh) return names[i];
    }
    return null;
  }

  function getSheet_(key) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const name = resolveName_(key);
    if (!name) throw new Error("Sheet not found for key: " + key);
    return ss.getSheetByName(name);
  }

  function getName_(key) {
    const name = resolveName_(key);
    if (!name) throw new Error("Sheet not found for key: " + key);
    return name;
  }

  return {
    getSheet_: getSheet_,
    getName_: getName_
  };

})();
