//ヤスショー自身が追加
document.addEventListener("DOMContentLoaded", function () {
  const links = document.querySelectorAll(".scroll-play");

  links.forEach(link => {
    link.addEventListener("click", function (e) {
      e.preventDefault();

      // 記事内で最初のYouTube iframeを取得
      const firstIframe = document.querySelector("iframe[src*='youtube.com']");

      if (firstIframe) {
        // 動画部分にスクロール
        firstIframe.scrollIntoView({ behavior: "smooth", block: "center" });

        // iframeのsrcを更新して特定秒数から再生
        const seconds = this.getAttribute("data-seconds");
        let videoUrl = firstIframe.getAttribute("src").split("?")[0]; // 基本のURLを取得
        const randomParam = `&_=${new Date().getTime()}`; // キャッシュ回避用パラメータ
        const newUrl = `${videoUrl}?start=${seconds}&autoplay=1${randomParam}`;
        firstIframe.setAttribute("src", newUrl);
      } else {
        console.error("YouTube動画が見つかりません");
      }
    });
  });
});
