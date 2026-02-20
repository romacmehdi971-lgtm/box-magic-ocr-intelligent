/**
 * G10_AUTH.gs
 * Token auth + anti-replay confirm_token mint/verify (usage unique).
 */

var IAPF_AUTH = (function () {

  function getApiMode_() {
    const props = PropertiesService.getScriptProperties();
    return String(props.getProperty("IAPF_API_MODE") || "SAFE");
  }

  function getToken_() {
    const props = PropertiesService.getScriptProperties();
    return String(props.getProperty("IAPF_API_TOKEN") || "");
  }

  function getAuditorToken_() {
    // Optional secondary token dedicated to read-only auditors (e.g. Élia).
    // If not set, only IAPF_API_TOKEN is accepted.
    const props = PropertiesService.getScriptProperties();
    return String(props.getProperty("IAPF_API_TOKEN_AUDITOR") || "");
  }

  function getSalt_() {
    const props = PropertiesService.getScriptProperties();
    return String(props.getProperty("IAPF_API_SALT") || "");
  }

  function authorizeRequest(token, req) {
    const expected = getToken_();
    if (!expected || expected.length < 24) {
      return { ok: false, reason: "API token not configured" };
    }

    var role = "";
    if (token && token === expected) {
      role = "OPERATOR";
    } else {
      const auditor = getAuditorToken_();
      if (auditor && auditor.length >= 24 && token === auditor) {
        role = "AUDITOR";
      } else {
        return { ok: false, reason: "Invalid token" };
      }
    }

    // minimal time sanity (avoid accidental replay with stale payload)
    // SAFE mode: reject if ts older than 10 minutes
    try {
      const mode = getApiMode_();
      if (mode === "SAFE") {
        const ts = new Date(String(req.ts || ""));
        const now = new Date();
        const ageMs = Math.abs(now.getTime() - ts.getTime());
        if (isNaN(ts.getTime())) return { ok: false, reason: "Invalid ts" };
        if (ageMs > 10 * 60 * 1000) return { ok: false, reason: "Stale request" };
      }
    } catch (e) {
      return { ok: false, reason: "Invalid ts" };
    }

    return { ok: true, role: role };
  }

  function mintConfirmToken(planObj) {
    // confirm token: short-lived nonce, usage unique
    // store in Script Cache or Properties (cache is better, but not always reliable across quotas)
    const nonce = Utilities.getUuid();
    const salt = getSalt_();
    const payload = JSON.stringify(planObj || {});
    const sig = Utilities.base64Encode(Utilities.computeHmacSha256Signature(payload + "|" + nonce, salt));
    const token = nonce + "." + sig;

    // store nonce as "unused" for 5 minutes
    CacheService.getScriptCache().put("IAPF_CONFIRM_" + nonce, "1", 300);

    return token;
  }

  function verifyAndConsumeConfirmToken(token, planObj) {
    if (!token || typeof token !== "string" || token.indexOf(".") === -1) return { ok: false, reason: "Invalid confirm token" };
    const parts = token.split(".");
    if (parts.length !== 2) return { ok: false, reason: "Invalid confirm token" };

    const nonce = parts[0];
    const sig = parts[1];

    // must exist and be unused
    const cache = CacheService.getScriptCache();
    const state = cache.get("IAPF_CONFIRM_" + nonce);
    if (!state) return { ok: false, reason: "Confirm token expired or already used" };

    const salt = getSalt_();
    const payload = JSON.stringify(planObj || {});
    const expectedSig = Utilities.base64Encode(Utilities.computeHmacSha256Signature(payload + "|" + nonce, salt));

    if (sig !== expectedSig) return { ok: false, reason: "Confirm token mismatch" };

    // consume
    cache.remove("IAPF_CONFIRM_" + nonce);

    return { ok: true };
  }

  return {
    getApiMode_: getApiMode_,
    authorizeRequest: authorizeRequest,
    mintConfirmToken: mintConfirmToken,
    verifyAndConsumeConfirmToken: verifyAndConsumeConfirmToken
  };

})();
