(function () {
  "use strict";

  function toNumber(value) {
    if (value === undefined || value === null || value === "") {
      return undefined;
    }
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  function parseQueryParam(search, key) {
    if (!search || !key) {
      return null;
    }
    var params = new URLSearchParams(search);
    return params.get(key);
  }

  function escapeHtml(value) {
    if (value == null) {
      return "";
    }
    if (window.L && window.L.Util && typeof window.L.Util.escapeHTML === "function") {
      return window.L.Util.escapeHTML(String(value));
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function buildPopupHtml(marker) {
    var title = marker.title || "";
    var description = marker.description || marker.body || "";
    var link = marker.link;
    var image = marker.image;
    var html = '<article class="gg-map__popup">';
    if (title) {
      html += '<h3 class="gg-map__popup-title">' + escapeHtml(title) + '</h3>';
    }
    if (description) {
      html += '<p class="gg-map__popup-body">' + escapeHtml(description) + '</p>';
    }
    if (image || link) {
      html += '<div class="gg-map__popup-meta">';
      if (image) {
        html += '<img class="gg-map__popup-image" src="' + escapeHtml(image) + '" alt="" loading="lazy">';
      }
      if (link) {
        var label = marker.linkLabel || "詳細を見る";
        html += '<a class="gg-map__popup-link" href="' + escapeHtml(link) + '" target="_blank" rel="noopener">' + escapeHtml(label) + '</a>';
      }
      html += '</div>';
    }
    html += '</article>';
    return html;
  }

  function createIcon(iconConfig) {
    if (!iconConfig || !window.L || !window.L.icon) {
      return undefined;
    }
    var options = Object.assign({}, iconConfig);
    if (Array.isArray(iconConfig.iconSize)) {
      options.iconSize = iconConfig.iconSize.map(Number);
    }
    if (Array.isArray(iconConfig.iconAnchor)) {
      options.iconAnchor = iconConfig.iconAnchor.map(Number);
    }
    if (Array.isArray(iconConfig.popupAnchor)) {
      options.popupAnchor = iconConfig.popupAnchor.map(Number);
    }
    return window.L.icon(options);
  }

  function addLayer(mapInstance, config, dataset) {
    var layerType = (config && config.type) || (dataset.tilesUrl ? "tile" : "");
    var layer;

    if (layerType === "image" && config && config.imageUrl && Array.isArray(config.bounds)) {
      layer = window.L.imageOverlay(config.imageUrl, config.bounds, config.options || {});
      layer.addTo(mapInstance);
      if (config.maxBounds) {
        mapInstance.setMaxBounds(config.maxBounds);
      }
      return layer;
    }

    var tileUrl = (config && config.url) || dataset.tilesUrl;
    if (!tileUrl) {
      return null;
    }
    var tileOptions = Object.assign(
      {
        minZoom: toNumber(dataset.minzoom),
        maxZoom: toNumber(dataset.maxzoom),
        minNativeZoom: toNumber(dataset.minnative),
        maxNativeZoom: toNumber(dataset.maxnative),
        attribution: dataset.attribution || undefined,
      },
      (config && config.options) || {}
    );
    Object.keys(tileOptions).forEach(function (key) {
      if (tileOptions[key] === undefined) {
        delete tileOptions[key];
      }
    });
    layer = window.L.tileLayer(tileUrl, tileOptions);
    layer.addTo(mapInstance);
    if (config && config.maxBounds) {
      mapInstance.setMaxBounds(config.maxBounds);
    }
    return layer;
  }

  function createFilters(container, categories, onToggle) {
    if (!categories.length) {
      return null;
    }
    var panel = document.createElement("aside");
    panel.className = "gg-map__filters";

    var heading = document.createElement("p");
    heading.className = "gg-map__filters-heading";
    heading.textContent = "カテゴリ";
    panel.appendChild(heading);

    var list = document.createElement("ul");
    list.className = "gg-map__filters-list";
    panel.appendChild(list);

    categories.forEach(function (category) {
      var item = document.createElement("li");
      item.className = "gg-map__filters-item";

      var input = document.createElement("input");
      input.type = "checkbox";
      input.className = "gg-map__filters-toggle";
      input.id = container.id + "-filter-" + category.id;
      input.checked = category.visible !== false;

      input.addEventListener("change", function () {
        onToggle(category.id, input.checked);
      });

      var label = document.createElement("label");
      label.className = "gg-map__filters-label";
      label.setAttribute("for", input.id);
      label.textContent = category.name || category.id;

      item.appendChild(input);
      item.appendChild(label);
      list.appendChild(item);
    });

    container.appendChild(panel);
    return panel;
  }

  function initMap(container) {
    if (!window.L) {
      console.warn("Leafletが未ロード");
      return;
    }

    var dataset = container.dataset;
    if (!dataset || !dataset.json) {
      console.warn("マップ定義JSONのパスが指定されていません", container);
      return;
    }

    fetch(dataset.json, { cache: "no-cache" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("JSONの読み込みに失敗しました: " + response.status);
        }
        return response.json();
      })
      .then(function (config) {
        renderMap(container, dataset, config);
      })
      .catch(function (error) {
        console.error(error);
      });
  }

  function renderMap(container, dataset, config) {
    var mapConfig = (config && config.map) || {};
    var viewConfig = mapConfig.view || {};

    var mapOptions = Object.assign(
      {
        center: viewConfig.center || [0, 0],
        zoom: toNumber(viewConfig.zoom) || toNumber(dataset.zoom) || 0,
        minZoom: toNumber(dataset.minzoom),
        maxZoom: toNumber(dataset.maxzoom),
        zoomControl: mapConfig.zoomControl !== false,
      },
      mapConfig.options || {}
    );

    if (mapConfig.crs === "Simple" && window.L.CRS && window.L.CRS.Simple) {
      mapOptions.crs = window.L.CRS.Simple;
    }

    var mapInstance = window.L.map(container, mapOptions);

    addLayer(mapInstance, mapConfig.layer, dataset);

    if (Array.isArray(viewConfig.bounds)) {
      mapInstance.fitBounds(viewConfig.bounds);
    }

    var categories = Array.isArray(config.categories) ? config.categories : [];
    var groups = new Map();
    var markerLookup = new Map();

    var filterCategories = [];

    categories.forEach(function (category, index) {
      var categoryId = category && category.id ? String(category.id) : "category-" + index;
      var categoryName = category.name || categoryId;
      var group = window.L.layerGroup();
      groups.set(categoryId, group);
      if (category.visible === false) {
        // leave group off map initially
      } else {
        group.addTo(mapInstance);
      }
      if (!Array.isArray(category.markers)) {
        return;
      }
      category.markers.forEach(function (marker) {
        if (!Array.isArray(marker.coords) || marker.coords.length < 2) {
          return;
        }
        var markerOptions = Object.assign({}, marker.options || {});
        var icon = createIcon(marker.icon);
        if (icon) {
          markerOptions.icon = icon;
        }
        var leafletMarker = window.L.marker(marker.coords, markerOptions);
        if (marker.popup !== false) {
          leafletMarker.bindPopup(buildPopupHtml(marker));
        }
        if (marker.tooltip) {
          leafletMarker.bindTooltip(marker.tooltip, { direction: "top", permanent: false });
        }
        leafletMarker.addTo(group);
        if (marker.id) {
          markerLookup.set(String(marker.id), leafletMarker);
        }
      });
      filterCategories.push({
        id: categoryId,
        name: categoryName,
        visible: category.visible !== false,
      });
    });

    var filterEnabled = dataset.filters === "on";
    if (filterEnabled && filterCategories.length) {
      if (!container.id) {
        container.id = "gg-map-" + Math.random().toString(36).slice(2, 9);
      }
      createFilters(container, filterCategories, function (categoryId, enabled) {
        var group = groups.get(categoryId);
        if (!group) {
          return;
        }
        if (enabled) {
          group.addTo(mapInstance);
        } else {
          mapInstance.removeLayer(group);
        }
      });
    }

    var openParamKey = dataset.openIdParam || "id";
    var markerId = parseQueryParam(window.location.search, openParamKey);
    if (markerId && markerLookup.has(markerId)) {
      markerLookup.get(markerId).openPopup();
    }
  }

  function bootstrap() {
    var containers = document.querySelectorAll(".gg-map");
    containers.forEach(initMap);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();
