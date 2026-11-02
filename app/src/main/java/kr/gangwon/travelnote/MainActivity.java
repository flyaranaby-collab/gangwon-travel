package kr.gangwon.travelnote;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * 강원 여행 수첩 앱.
 * 앱 안에 들어 있는 수첩(assets/index.html)을 보여 주고, 켤 때마다 GitHub에 올라간
 * 최신 수첩(web/index.html)이 있는지 확인해 새 버전이면 내려받아 바로 바꿔 보여 준다.
 * 그래서 장소·문구가 바뀌어도 앱을 다시 설치할 필요가 없다.
 */
public class MainActivity extends Activity {
    // 최신 수첩이 올라가는 곳 (GitHub 저장소 flyaranaby-collab/gangwon-travel 의 web 폴더)
    private static final String BASE = "https://raw.githubusercontent.com/flyaranaby-collab/gangwon-travel/main/web/";
    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#0A1324"));
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // 내 코스·스탬프·후기 저장
        s.setAllowFileAccess(true);
        s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("file".equals(u.getScheme())) return false;
                // 지도·예매·블로그 링크와 카카오T 같은 앱 링크는 휴대폰의 브라우저나 해당 앱으로 연다
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (ActivityNotFoundException e) {
                    if ("kakaot".equals(u.getScheme())) {
                        openUrl("https://play.google.com/store/apps/details?id=com.kakao.taxi");
                    } else {
                        Toast.makeText(MainActivity.this, "이 링크를 열 앱이 없어요.", Toast.LENGTH_SHORT).show();
                    }
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

    private File localPage() { return new File(getFilesDir(), "www/index.html"); }
    private File localVersion() { return new File(getFilesDir(), "www/version.txt"); }

    /** 내려받아 둔 최신 수첩이 앱에 든 것보다 새것이면 그걸, 아니면 앱에 든 수첩을 연다 */
    private String pageUrl() {
        if (localPage().exists() && readLocalVersion() > bundledVersion()) {
            return "file://" + localPage().getAbsolutePath();
        }
        return "file:///android_asset/index.html";
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
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        return out.toByteArray();
    }

    private static byte[] get(String url) throws java.io.IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url + "?t=" + System.currentTimeMillis()).openConnection();
        c.setConnectTimeout(8000);
        c.setReadTimeout(20000);
        c.setUseCaches(false);
        try (InputStream in = c.getInputStream()) { return readAll(in); }
        finally { c.disconnect(); }
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
                if (page.length < 10000 || !text.contains("tab-places")) return;   // 받다 끊긴 파일은 쓰지 않는다
                File dir = localPage().getParentFile();
                if (dir != null && !dir.exists()) dir.mkdirs();
                try (FileOutputStream o = new FileOutputStream(localPage())) { o.write(page); }
                try (FileOutputStream o = new FileOutputStream(localVersion())) { o.write(String.valueOf(remote).getBytes(StandardCharsets.UTF_8)); }
                runOnUiThread(() -> {
                    Toast.makeText(this, "수첩을 최신 내용으로 업데이트했어요.", Toast.LENGTH_SHORT).show();
                    web.loadUrl(pageUrl());
                });
            } catch (Exception ignored) { }
        }).start();
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
}
