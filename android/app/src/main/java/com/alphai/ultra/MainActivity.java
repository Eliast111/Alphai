package com.alphai.ultra;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.content.Intent;
import android.net.Uri;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;

public class MainActivity extends Activity {

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().setStatusBarColor(0xFF080D18);
        getWindow().setNavigationBarColor(0xFF080D18);

        webView = new WebView(this);

        webView.setBackgroundColor(0xFF080D18);

        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setDatabaseEnabled(true);
        webView.getSettings().setSafeBrowsingEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(
                    WebView view, WebResourceRequest request) {

                String url = request.getUrl().toString();

                if (url.startsWith(BuildConfig.WEB_APP_URL)) {
                    return false;
                }

                if (url.startsWith("https://")) {
                    startActivity(new Intent(
                        Intent.ACTION_VIEW, Uri.parse(url)));
                    return true;
                }

                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient());

        setContentView(webView);

        webView.loadUrl(BuildConfig.WEB_APP_URL);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
