export async function api(url, options = {}) {
  const r = await fetch("/api" + url, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  let data;
  try {
    data = await r.json();
  } catch {
    throw new Error(
      "The server returned an unexpected response. Please retry.",
    );
  }
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}
export const money = (n, currency = "INR") =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(n);
