export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, options);
  const body = await response.text();
  let payload = {};
  if (body) {
    try {
      payload = JSON.parse(body);
    } catch {
      if (response.ok) throw new Error("The API returned an invalid response.");
    }
  }
  if (!response.ok) {
    const message = payload.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

export async function fetchResource(path) {
  return api(path);
}

export function csvUrl(rows, columns) {
  const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const body = [
    columns.join(","),
    ...rows.map((row) => columns.map((column) => escape(row[column])).join(",")),
  ].join("\r\n");
  return URL.createObjectURL(new Blob([body], { type: "text/csv;charset=utf-8" }));
}
