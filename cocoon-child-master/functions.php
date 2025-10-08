<?php //子テーマ用関数
if ( !defined( 'ABSPATH' ) ) exit;

//子テーマ用のビジュアルエディタースタイルを適用
add_editor_style();

//以下に子テーマ用の関数を書く




// prism.jsを有効化
function my_prism() {
	wp_enqueue_style( 'prism-style', get_stylesheet_directory_uri() . '/css/prism.css' ); // 第2引数には自身がファイルをアップロードしたパスを指定
	wp_enqueue_script( 'prism-script', get_stylesheet_directory_uri() . '/js/prism.js', array('jquery'), '1.9.0', true ); // 第2引数には自身がファイルをアップロードしたパスを指定
}
add_action( 'wp_enqueue_scripts', 'my_prism' );


//ヤスショー自身が追記_

function enqueue_leaflet_fullscreen_scripts() {
    // Leafletの基本ファイルを読み込む
    wp_enqueue_style('leaflet-css', get_template_directory_uri() . '/leaflet/leaflet.css', array(), '1.9.4');
    wp_enqueue_script('leaflet-js', get_template_directory_uri() . '/leaflet/leaflet.js', array(), '1.9.4', true);

    // Leaflet Fullscreenプラグインのファイルを読み込む
    wp_enqueue_style('leaflet-fullscreen-css', get_template_directory_uri() . '/leaflet/leaflet.fullscreen.css', array('leaflet-css'), '1.0.1');
    wp_enqueue_script('leaflet-fullscreen-js', get_template_directory_uri() . '/leaflet/Leaflet.fullscreen.js', array('leaflet-js'), '1.0.1', true);
}
add_action('wp_enqueue_scripts', 'enqueue_leaflet_fullscreen_scripts');

//ヤスショー自身が追記_Youtube再生ボタン
function enqueue_custom_scroll_script() {
    if (is_single()) { // 投稿ページでのみスクリプトを読み込む
        wp_enqueue_script(
            'custom-scroll-play',
            get_stylesheet_directory_uri() . '/js/custom-scroll-play.js',
            array(),
            null,
            true // フッターで読み込む
        );
    }
}
add_action('wp_enqueue_scripts', 'enqueue_custom_scroll_script');

// ヤスショー自身が追記_カービィディスカバリー（拡張：X/Y対応 & 地図で確認リンク）
add_shortcode('custom_cards', function($atts, $content = null) {
  return custom_card_sequence_shortcode($atts, shortcode_unautop($content));
});

function custom_card_sequence_shortcode($atts, $content = null) {
  if (!$content) return '';

  // <br> で分割してカードを解析
  $lines = array_map('trim', preg_split('/<br\s*\/?>/i', trim($content)));
  $cards = [];

  foreach ($lines as $line) {
    if (strpos($line, ',') !== false) {
      $parts   = explode(',', $line);

      $img     = trim($parts[0] ?? '');
      $text    = trim($parts[1] ?? '');
      $seconds = isset($parts[2]) ? intval(trim($parts[2])) : null;

      // 4列目：X座標（任意） / 5列目：Y座標（任意）
      $x_raw = isset($parts[3]) ? trim($parts[3]) : null;
      $y_raw = isset($parts[4]) ? trim($parts[4]) : null;

      // 数値として妥当なら float に、そうでなければ null
      $x = (isset($x_raw) && $x_raw !== '' && is_numeric($x_raw)) ? (float)$x_raw : null;
      $y = (isset($y_raw) && $y_raw !== '' && is_numeric($y_raw)) ? (float)$y_raw : null;

      $cards[] = [
        'img'     => $img,
        'text'    => wp_kses_post($text),
        'seconds' => $seconds,
        'x'       => $x,
        'y'       => $y,
      ];
    }
  }

  if (empty($cards)) return '<p>カードデータが無効です。</p>';

  ob_start();
  echo '<div style="background-color: #f5f0b3; padding: 20px; border-radius: 20px;">';

  $total = count($cards);
  foreach ($cards as $index => $card) {
    $image   = esc_url($card['img']);
    $text    = $card['text'];
    $seconds = $card['seconds'];
    $x       = $card['x'];
    $y       = $card['y'];

    echo '<div style="background-color: #96faff; margin: 0 auto; margin-bottom: 10px; padding: 15px; display: flex; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">';
      echo '<img src="' . $image . '" alt="画像" style="width: 80px; height: 80px; margin-right: 20px;">';
      echo '<div><p>' . $text . '</p>';

      // 動画リンク（秒数があるときのみ）
      if (!is_null($seconds)) {
        echo '<p><a href="javascript:void(0)" class="scroll-play" data-seconds="' . intval($seconds) . '">動画で確認</a></p>';
      }

      // 地図リンク（X/Y 両方あるときのみ）
      if (!is_null($x) && !is_null($y)) {
        // ご指定の形：onclick="JumpTo(X座標,Y座標),4"
        // 数値はそのまま埋め込み（JS側で JumpTo() を実装しておいてください）
        echo '<p><a href="#mapanc" type="submit" onclick="JumpTo(' . $x . ',' . $y . ',4)">地図で確認</a></p>';
      }

      echo '</div>';
    echo '</div>';

    // 矢印（最後のカード以外）
    if ($index < $total - 1) {
      echo '<div style="text-align: center; margin: 10px 0;">';
      echo '<div style="width: 0; height: 0; border-left: 20px solid transparent; border-right: 20px solid transparent; border-top: 30px solid red; display: inline-block;"></div>';
      echo '</div>';
    }
  }

  echo '</div>';
  return ob_get_clean();
}


// 男の子「マナブ君」吹き出しショートコード
function my_speech_boy_shortcode($atts, $content = null) {
    // 属性の初期値（必要に応じて上書き可能）
    $atts = shortcode_atts(
        array(
            'img'  => 'https://yasusho-topics.com/wp-content/uploads/2025/08/manabu.png', // デフォルト画像
            'alt'  => 'マナブ君',
            'name' => 'マナブ君',
            'id'   => '23',
        ),
        $atts,
        'speech_boy'
    );

    ob_start();
    ?>
    <div class="speech-wrap sb-id-<?php echo esc_attr($atts['id']); ?> sbs-stn sbp-l sbis-cb cf">
        <div class="speech-person">
            <figure class="speech-icon">
                <img class="speech-icon-image"
                     src="<?php echo esc_url($atts['img']); ?>"
                     alt="<?php echo esc_attr($atts['alt']); ?>"
                     width="160" height="160" />
            </figure>
            <div class="speech-name"><?php echo esc_html($atts['name']); ?></div>
        </div>
        <div class="speech-balloon">
            <?php echo do_shortcode($content); ?>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('speech_boy', 'my_speech_boy_shortcode');

// 「先生」吹き出しショートコード
function my_speech_teacher_shortcode($atts, $content = null) {
    // 属性の初期値（必要に応じて上書き可能）
    $atts = shortcode_atts(
        array(
            'img'  => 'https://yasusho-topics.com/wp-content/uploads/2025/08/teacher.png', // デフォルト画像
            'alt'  => '先生',
            'name' => '先生',
            'id'   => '25',
        ),
        $atts,
        'speech_teacher'
    );

    ob_start();
    ?>
    <div class="speech-wrap sb-id-<?php echo esc_attr($atts['id']); ?> sbs-stn sbp-l sbis-sn cf">
        <div class="speech-person">
            <figure class="speech-icon">
                <img class="speech-icon-image"
                     src="<?php echo esc_url($atts['img']); ?>"
                     alt="<?php echo esc_attr($atts['alt']); ?>"
                     width="160" height="160" />
            </figure>
            <div class="speech-name"><?php echo esc_html($atts['name']); ?></div>
        </div>
        <div class="speech-balloon">
            <?php echo do_shortcode($content); ?>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('speech_teacher', 'my_speech_teacher_shortcode');

