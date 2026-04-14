import https from "node:https";
import { URL } from "node:url";

const target = process.argv[2] || "https://www.viistock.io.vn/";
const expectedNeedle = process.argv[3] || "Newsfeed tín hiệu mua";

function fetchRaw(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = https.request(
      {
        protocol: parsed.protocol,
        hostname: parsed.hostname,
        port: parsed.port || 443,
        path: parsed.pathname + parsed.search,
        method: "GET",
        headers: {
          Host: parsed.hostname,
          "User-Agent": "homepage-verify/1.0",
          Accept: "text/html,*/*",
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          resolve({
            statusCode: res.statusCode || 0,
            headers: res.headers,
            body,
          });
        });
      },
    );
    req.on("error", reject);
    req.end();
  });
}

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exit(1);
}

const response = await fetchRaw(target);
const location = response.headers.location;
const refresh = response.headers.refresh;

if (response.statusCode >= 300 && response.statusCode < 400) {
  fail(`Homepage returned redirect status ${response.statusCode} (location=${location || "none"})`);
}

if (location || refresh) {
  fail(`Homepage has redirect headers (location=${location || "none"}, refresh=${refresh || "none"})`);
}

if (response.statusCode !== 200) {
  fail(`Homepage returned non-200 status ${response.statusCode}`);
}

if (!response.body.includes(expectedNeedle)) {
  fail(`Homepage body does not include expected marker: "${expectedNeedle}"`);
}

console.log(`OK: ${target} returns 200 with newsfeed marker and no redirect headers.`);
