package kr.gangwon.travelnote;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.webkit.WebViewAssetLoader;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * 강원 여행 수첩 앱.
 * 앱 안에 든 수첩(assets/index.html)을 보여 주고, 켤 때마다 GitHub의 최신 수첩이 있는지 확인해
 * 새 버전이면 내려받아 바꿔 보여 준다.
 *
 * 보안: 휴대폰 파일에 직접 접근하는 file:// 방식 대신, 안드로이드 권장 방식(WebViewAssetLoader)으로
 * https://appassets.androidplatform.net 주소 아래에서 앱 안 파일만 보여 준다.
 */
public class MainActivity extends Activity {
    private static final String BASE = "https://raw.githubusercontent.com/flyaranaby-collab/gangwon-travel/main/web/";
    private static final String HOST = "https://appassets.androidplatform.net";
    // 휴대폰의 다른 앱으로 넘겨도 되는 링크 종류(지도·전화·카카오T 등). 그 밖의 형식은 열지 않는다.
    private static final Set<String> EXTERNAL = new HashSet<>(Arrays.asList(
            "http", "https", "tel", "mailto", "geo", "sms", "kakaot", "kakaomap", "nmap", "market"));
    private WebView web;
    private WebViewAssetLoader loader;
    private ValueCallback<Uri[]> fileCallback;
    private static final int PICK_FILE = 41;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#0A1324"));
        File www = wwwDir();
        if (!www.exists()) www.mkdirs();
        loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .addPathHandler("/www/", new WebViewAssetLoader.InternalStoragePathHandler(this, www))
                .build();

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);           // 내 코스·스탬프·후기 저장
        s.setAllowFileAccess(false);            // 휴대폰 파일 접근 차단
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setSafeBrowsingEnabled(true);         // 구글 세이프 브라우징으로 위험한 주소 차단
        s.setGeolocationEnabled(false);
        s.setSupportMultipleWindows(false);
        s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                return loader.shouldInterceptRequest(req.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("appassets.androidplatform.net".equals(u.getHost())) return false;
                String scheme = u.getScheme() == null ? "" : u.getScheme().toLowerCase();
                if (!EXTERNAL.contains(scheme)) return true;     // javascript:, file:, intent: 등은 막는다
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, u).addCategory(Intent.CATEGORY_BROWSABLE));
                } catch (ActivityNotFoundException e) {
                    if ("kakaot".equals(scheme)) {
                        openUrl("https://play.google.com/store/apps/details?id=com.kakao.taxi");
                    } else {
                        Toast.makeText(MainActivity.this, "이 링크를 열 앱이 없어요.", Toast.LENGTH_SHORT).show();
                    }
                }
                return true;
            }
        });
        // 운영자 사진 등록(사진첩·카메라 선택 창)과 확인·입력 창을 쓸 수 있게 한다
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> cb, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                try {
                    startActivityForResult(params.createIntent(), PICK_FILE);
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    Toast.makeText(MainActivity.this, "사진을 고를 앱이 없어요.", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });
        setContentView(web);
        if (savedInstanceState != null) web.restoreState(savedInstanceState);
        else web.loadUrl(pageUrl());
        checkUpdate();
    }

    private void openUrl(String url) {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) {}
    }

    private File wwwDir() { return new File(getFilesDir(), "www"); }
    private File localPage() { return new File(wwwDir(), "index.html"); }
    private File localVersion() { return new File(wwwDir(), "version.txt"); }

    /** 내려받아 둔 최신 수첩이 앱에 든 것보다 새것이면 그걸, 아니면 앱에 든 수첩을 연다 */
    private String pageUrl() {
        if (localPage().exists() && readLocalVersion() > bundledVersion()) return HOST + "/www/index.html";
        return HOST + "/assets/index.html";
    }

    private long bundledVersion() {
        try (InputStream in = getAssets().open("version.txt")) {
            return parse(new String(readAll(in), StandardCharsets.UTF_8));
        } catch (Exception e) { return 0; }
    }

    private long readLocalVersion() {
        try (InputStream in = new java.io.FileInputStream(localVersion())) {
            return parse(new String(readAll(in), StandardCharsets.UTF_8));
        } catch (Exception e) { return 0; }
    }

    private static long parse(String s) {
        try { return Long.parseLong(s.trim()); } catch (Exception e) { return 0; }
    }

    private static byte[] readAll(InputStream in) throws java.io.IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) > 0) {
            out.write(buf, 0, n);
            if (out.size() > 20_000_000) throw new java.io.IOException("too large");
        }
        return out.toByteArray();
    }

    private static byte[] get(String url) throws java.io.IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url + "?t=" + System.currentTimeMillis()).openConnection();
        c.setConnectTimeout(8000);
        c.setReadTimeout(20000);
        c.setUseCaches(false);
        c.setInstanceFollowRedirects(false);
        try {
            if (c.getResponseCode() != 200) throw new java.io.IOException("HTTP " + c.getResponseCode());
            try (InputStream in = c.getInputStream()) { return readAll(in); }
        } finally { c.disconnect(); }
    }

    /** 인터넷이 될 때 최신 수첩이 있는지 확인. 실패하면 조용히 지금 것을 계속 쓴다. */
    private void checkUpdate() {
        new Thread(() -> {
            try {
                long remote = parse(new String(get(BASE + "version.txt"), StandardCharsets.UTF_8));
                long current = Math.max(bundledVersion(), readLocalVersion());
                if (remote <= current) return;
                byte[] page = get(BASE + "index.html");
                String text = new String(page, StandardCharsets.UTF_8);
                // 받다 끊겼거나 엉뚱한 파일이면 쓰지 않는다
                if (page.length < 10000 || !text.contains("tab-places") || !text.contains("window.APK_BUILD=true")) return;
                File tmp = new File(wwwDir(), "index.html.part");
                try (FileOutputStream o = new FileOutputStream(tmp)) { o.write(page); }
                if (!tmp.renameTo(localPage())) return;
                try (FileOutputStream o = new FileOutputStream(localVersion())) { o.write(String.valueOf(remote).getBytes(StandardCharsets.UTF_8)); }
                runOnUiThread(() -> {
                    Toast.makeText(this, "수첩을 최신 내용으로 업데이트했어요.", Toast.LENGTH_SHORT).show();
                    web.loadUrl(pageUrl());
                });
            } catch (Exception ignored) { }
        }).start();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_FILE || fileCallback == null) return;
        fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
        fileCallback = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (web != null) { web.stopLoading(); web.destroy(); }
        super.onDestroy();
    }
}
