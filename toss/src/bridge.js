// 토스 앱 기능(광고·뒤로 가기·외부 링크·위치·공유)을 수첩 화면에서 쓸 수 있게 window.AIT로 꺼내 둔다.
import { TossAds, graniteEvent, Device, closeView, Share, Accuracy, getOperationalEnvironment } from "@apps-in-toss/web-framework";
window.AIT = { TossAds, graniteEvent, Device, closeView, Share, Accuracy, env: () => { try { return getOperationalEnvironment(); } catch (_) { return null; } } };
