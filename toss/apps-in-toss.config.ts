import { defineConfig } from "@apps-in-toss/web-framework/config";

// appName은 앱인토스 콘솔에 등록한 이름과 똑같아야 업로드돼요. 콘솔에서 다른 이름으로 만들었다면 여기만 바꾸세요.
export default defineConfig({
  appName: "gangwon-note",
  permissions: [
    { name: "geolocation", access: "access" }, // 내 주변·거리 표시(사용자가 버튼을 눌렀을 때만 물어봄)
  ],
  navigationBar: {
    withBackButton: true, // 토스 뒤로 가기만 쓰고, 수첩 자체 뒤로 가기 버튼은 숨겨요
    withHomeButton: false,
    withTitle: true,
  },
  webView: {
    bounces: true,
    pullToRefreshEnabled: false,
    allowsBackForwardNavigationGestures: false,
  },
  webBundleDir: "dist",
});
