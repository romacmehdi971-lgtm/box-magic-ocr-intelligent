/**
 * G09_API_ENDPOINT.gs
 * WebApp entrypoint: doPost/doGet -> secure dispatcher
 */

function doPost(e) {
  return IAPF_API.handleRequest_(e);
}

function doGet(e) {
  // Healthcheck minimal, no secrets, no internal details.
  const out = {
    ok: true,
    service: "IAPF_MCP_WEBAPP",
    mode: IAPF_API.getMode_(),
    time: new Date().toISOString()
  };
  return ContentService
    .createTextOutput(JSON.stringify(out))
    .setMimeType(ContentService.MimeType.JSON);
}

var IAPF_API = (function () {

  function handleRequest_(e) {
    const nowIso = new Date().toISOString();
    let requestId = "unknown";
    try {
      const rawBody = (e && e.postData && e.postData.contents) ? e.postData.contents : "";
      const headers = (e && e.parameter) ? e.parameter : {}; // Note: WebApp doesn't pass headers directly
      // We'll read token via query param fallback ONLY if needed (discouraged).
      // Recommended: token in body for WebApp limitation unless using external proxy.
      const parsed = rawBody ? JSON.parse(rawBody) : {};

      requestId = (parsed && parsed.request_id) ? String(parsed.request_id) : "unknown";
      const token = extractToken_(e, parsed);

      // AUTH
      const auth = IAPF_AUTH.authorizeRequest(token, parsed);
      if (!auth.ok) {
        safeLog_(nowIso, "CONSTAT", "API_AUTH_REFUSED", {
          request_id: requestId,
          reason: auth.reason
        }, "API");
        return jsonOut_(403, {
          ok: false,
          mode: getMode_(),
          request_id: requestId,
          dry_run: true,
          errors: [{ code: "AUTH_REFUSED", message: auth.reason }]
        });
      }

      // Attach role to request for downstream gating (dispatcher).
      // Note: keep internal field name underscore-prefixed to avoid collisions.
      parsed._auth = { role: String(auth.role || "OPERATOR") };

      // VALIDATE ENVELOPE
      const v = validateEnvelope_(parsed);
      if (!v.ok) {
        safeLog_(nowIso, "CONSTAT", "API_INVALID_REQUEST", {
          request_id: requestId,
          errors: v.errors
        }, "API");
        return jsonOut_(400, {
          ok: false,
          mode: getMode_(),
          request_id: requestId,
          dry_run: true,
          errors: v.errors
        });
      }

      // DISPATCH
      const dispatch = IAPF_DISPATCH.dispatch(parsed);

      // LOG (always)
      safeLog_(nowIso,
        dispatch.ok ? (dispatch.dry_run ? "CONSTAT" : "DECISION") : "CONSTAT",
        dispatch.log_title,
        dispatch.log_details,
        "API"
      );

      return jsonOut_(200, dispatch.response);

    } catch (err) {
      safeLog_(nowIso, "CONSTAT", "API_CRASH", {
        request_id: requestId,
        message: String(err && err.message ? err.message : err)
      }, "API");

      return jsonOut_(500, {
        ok: false,
        mode: getMode_(),
        request_id: requestId,
        dry_run: true,
        errors: [{ code: "SERVER_ERROR", message: "Internal error" }]
      });
    }
  }

  function extractToken_(e, parsed) {
    // WebApp header access is limited; safest pragmatic approach:
    // token must be in body: parsed.auth.token
    // (If you later add a proxy, you can pass headers to body.)
    if (parsed && parsed.auth && parsed.auth.token) return String(parsed.auth.token);

    // Optional fallback: ?token=... for emergency manual tests (not recommended)
    if (e && e.parameter && e.parameter.token) return String(e.parameter.token);

    return "";
  }

  function validateEnvelope_(req) {
    const errors = [];
    if (!req || typeof req !== "object") {
      return { ok: false, errors: [{ code: "INVALID_JSON", message: "Body must be JSON object" }] };
    }
    if (!req.action || typeof req.action !== "string") errors.push({ code: "MISSING_ACTION", message: "action is required" });
    if (!req.request_id || typeof req.request_id !== "string") errors.push({ code: "MISSING_REQUEST_ID", message: "request_id is required" });
    if (!req.ts || typeof req.ts !== "string") errors.push({ code: "MISSING_TS", message: "ts is required" });

    // payload can be absent; will default to {}
    if (req.payload && typeof req.payload !== "object") errors.push({ code: "INVALID_PAYLOAD", message: "payload must be object" });

    // confirm is optional boolean
    if (req.confirm !== undefined && typeof req.confirm !== "boolean") {
      errors.push({ code: "INVALID_CONFIRM", message: "confirm must be boolean" });
    }

    // confirm_token required only when confirm=true
    if (req.confirm === true && (!req.confirm_token || typeof req.confirm_token !== "string")) {
      errors.push({ code: "MISSING_CONFIRM_TOKEN", message: "confirm_token required when confirm=true" });
    }

    return { ok: errors.length === 0, errors: errors };
  }

  function jsonOut_(statusCode, obj) {
    // Apps Script ContentService doesn't allow setting HTTP status.
    // We'll embed status in response for client handling.
    const payload = Object.assign({ http_status: statusCode }, obj);
    return ContentService
      .createTextOutput(JSON.stringify(payload))
      .setMimeType(ContentService.MimeType.JSON);
  }

  function safeLog_(tsIso, type, title, detailsObj, source) {
    // Always log via MEMORY_LOG writer (existing function)
    try {
      const details = JSON.stringify(detailsObj || {});
      IAPF_appendMemoryEntry(tsIso, type, title, details, Session.getActiveUser().getEmail() || "system", source || "API", "IAPF;MCP;API");
    } catch (e) {
      // last resort: avoid throwing
      try { Logger.log("LOG_FAIL " + String(e)); } catch (_) {}
    }
  }

  function getMode_() {
    return IAPF_AUTH.getApiMode_();
  }

  return {
    handleRequest_: handleRequest_,
    getMode_: getMode_
  };

})();
