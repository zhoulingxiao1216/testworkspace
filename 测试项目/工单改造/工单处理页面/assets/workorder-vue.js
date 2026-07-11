(function () {
  function revealCloaked() {
    document.querySelectorAll("[v-cloak]").forEach(function (element) {
      element.removeAttribute("v-cloak");
    });
  }

  function setBootMessage(message, isError) {
    var target = document.getElementById("vueBootError");
    if (!target) {
      document.body.insertAdjacentHTML("afterbegin", '<div id="vueBootError" class="boot-message"></div>');
      target = document.getElementById("vueBootError");
    }
    target.textContent = message;
    target.className = "boot-message" + (isError ? " is-error" : "");
  }

  function markBootReady() {
    var target = document.getElementById("vueBootError");
    if (target) target.className = "boot-message is-hidden";
  }

  window.addEventListener("error", function (event) {
    setBootMessage("页面加载失败：" + (event.message || "未知错误"), true);
    revealCloaked();
  });

  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason || {};
    setBootMessage("页面加载失败：" + (reason.message || reason || "未知错误"), true);
    revealCloaked();
  });

  if (!window.Vue) {
    setBootMessage("Vue 资源未加载，请检查 assets/vue.global.prod.js 是否存在。", true);
    revealCloaked();
    return;
  }

  var createApp = window.Vue.createApp;
  var STORAGE_VERSION = 9;
  var STORAGE_KEY = "global-v2-workorder-simple-flow-v9";
  var LEGACY_STORAGE_KEYS = [
    "global-v2-workorder-simple-flow",
    "global-v2-workorder-simple-flow-v1",
    "global-v2-workorder-simple-flow-v2",
    "global-v2-workorder-simple-flow-v3",
    "global-v2-workorder-simple-flow-v4",
    "global-v2-workorder-simple-flow-v5",
    "global-v2-workorder-simple-flow-v6",
    "global-v2-workorder-simple-flow-v7",
    "global-v2-workorder-simple-flow-v8"
  ];
  var ORDER_NO = "B2B-DD-KOR8-260517-144";
  var CUSTOMER_NO = "D-KOR8-TEST-1010";
  var CURRENT_USER = "订单业务 唐芬芬";
  var BUSINESS_HANDLER = "订单业务 唐芬芬";
  var DEMO_PROPOSER = "仓库主管 丁超";
  var LEGACY_DEMO_PROPOSER = "质检主管 李倩";

  var people = [
    { value: "订单业务 唐芬芬", role: "业务", desc: "整理对客内容并发送客户确认" },
    { value: "采购 包瑞楠", role: "采购", desc: "确认供应商方案、货源和补偿" },
    { value: "仓库主管 丁超", role: "仓库", desc: "确认库存、入库或发货状态" },
    { value: "客户经理 金月明", role: "客户经理", desc: "确认客户侧订单责任人" },
    { value: "A组组长 王小燕", role: "质控", desc: "A组组长" },
    { value: "A组初检 李林玉", role: "质控", desc: "A组初检" },
    { value: "B组组长 张双", role: "质控", desc: "B组组长" },
    { value: "B组初检 王盈盈", role: "质控", desc: "B组初检" },
    { value: "B组初检 代秋艳", role: "质控", desc: "B组初检" },
    { value: "C组组长 梅慧慧", role: "质控", desc: "C组组长" },
    { value: "C组初检 宋科慧", role: "质控", desc: "C组初检" },
    { value: "D组组长 王菊", role: "质控", desc: "D组组长" },
    { value: "D组初检 崔明花", role: "质控", desc: "D组初检" },
    { value: "E组组长 丁路生", role: "质控", desc: "E组组长" },
    { value: "E组初检 岳飞燕", role: "质控", desc: "E组初检" }
  ];

  var templateLanguages = [
    { key: "zh", label: "中文" },
    { key: "en", label: "英语" },
    { key: "ja", label: "日语" },
    { key: "ko", label: "韩语" },
    { key: "ar", label: "阿拉伯语" },
    { key: "es", label: "西班牙语" },
    { key: "ru", label: "俄语" }
  ];

  function emptyTranslations() {
    return templateLanguages.reduce(function (result, language) {
      result[language.key] = "";
      return result;
    }, {});
  }

  function makeIssueTemplate(config) {
    var translations = Object.assign(emptyTranslations(), config.translations || {});
    return {
      id: config.id || uid("tpl_"),
      name: config.name || "未命名模板",
      enabled: config.enabled !== false,
      translations: translations,
      updatedAt: config.updatedAt || "刚刚"
    };
  }

  var defaultIssueTemplates = [
    makeIssueTemplate({
      id: "tpl_color_diff",
      name: "色差问题",
      translations: {
        zh: "检验概况：抽检样品同款式衣物，面料色调存在明显偏差，不同单件、衣身拼接处色泽深浅不一，正反面色彩观感差异显著。\n判定标准：未达到同批次服饰色泽统一出厂要求，色差超出合格允许范围。\n整改意见：分拣隔离异色货品，调整染色工艺，复检合格后方可入库出货。",
        en: "Inspection overview: Randomly inspected samples of the same clothing style show obvious deviations in fabric color tone. Color depth varies between individual pieces and at garment seam areas, with significant visual differences between the front and back sides.\nJudgment standard: The goods do not meet the factory requirement for uniform color within the same garment batch, and the color difference exceeds the allowable qualified range.\nCorrective action: Sort and isolate off-color goods, adjust the dyeing process, and allow warehousing or shipment only after re-inspection passes.",
        ja: "検査概況：同一スタイルの衣類サンプルを抜き取り検査したところ、生地の色調に明らかな差異があり、個体間および身頃の接ぎ部分で色の濃淡が不均一で、表裏の色の見え方にも大きな差があります。\n判定基準：同一ロットの衣類に求められる色調統一の出荷基準を満たしておらず、色差が合格許容範囲を超えています。\n是正意見：色違い品を仕分け・隔離し、染色工程を調整したうえで、再検査合格後に入庫・出荷してください。",
        ko: "검사 개요: 동일 스타일 의류 샘플을 추출 검사한 결과, 원단 색조에 뚜렷한 편차가 있으며, 개별 제품 및 몸판 이음 부위의 색상 농담이 고르지 않고 앞뒷면 색감 차이도 뚜렷합니다.\n판정 기준: 동일 로트 의류의 색상 통일 출고 요구 기준에 미달하며, 색차가 합격 허용 범위를 초과했습니다.\n개선 의견: 색상이 다른 제품을 분류 및 격리하고, 염색 공정을 조정한 뒤 재검사 합격 후 입고 및 출고해야 합니다.",
        ar: "نظرة عامة على الفحص: أظهر فحص عينات عشوائية من ملابس بنفس الموديل وجود اختلاف واضح في درجة لون القماش، مع تفاوت في عمق اللون بين القطع المختلفة وعند مناطق وصل أجزاء الثوب، كما أن الانطباع اللوني بين الوجه الأمامي والخلفي مختلف بشكل ملحوظ.\nمعيار الحكم: لا يفي بمتطلبات توحيد اللون لملابس نفس الدفعة عند الخروج من المصنع، ويتجاوز فرق اللون نطاق القبول المسموح به.\nإجراء التصحيح: فرز وعزل المنتجات ذات اللون المختلف، وضبط عملية الصباغة، ولا يسمح بالإدخال إلى المخزن أو الشحن إلا بعد اجتياز إعادة الفحص.",
        es: "Resumen de inspección: La inspección por muestreo de prendas del mismo modelo muestra una desviación evidente en el tono de la tela. Hay diferencias de intensidad de color entre piezas y en las uniones del cuerpo de la prenda, y la apariencia de color entre el frente y el reverso difiere notablemente.\nCriterio de evaluación: No cumple con el requisito de uniformidad de color para prendas del mismo lote antes de la salida de fábrica; la diferencia de color supera el rango permitido.\nAcción correctiva: Separar y aislar las piezas con color diferente, ajustar el proceso de teñido y permitir la entrada en almacén o el envío solo después de aprobar la reinspección.",
        ru: "Обзор проверки: Выборочная проверка изделий одного фасона показала заметное отклонение оттенка ткани; глубина цвета отличается между отдельными изделиями и в местах соединения деталей, а визуальное восприятие цвета лицевой и изнаночной сторон существенно различается.\nКритерий оценки: Не соответствует требованию единообразия цвета для одежды одной партии перед выпуском; цветовое различие превышает допустимый диапазон.\nКорректирующие меры: Отсортировать и изолировать изделия с отличающимся цветом, скорректировать процесс окрашивания, допускать на склад и к отгрузке только после успешной повторной проверки."
      },
      updatedAt: "2026-05-23 09:00"
    }),
    makeIssueTemplate({
      id: "tpl_size_issue",
      name: "尺寸问题",
      translations: {
        zh: "检验概况：实测衣长、胸围、袖长等关键尺寸，多处与图纸标准参数不符，单件之间尺寸误差偏大，超出公差允许区间。\n判定标准：版型尺寸不达标，易出现穿着版型走样问题。\n整改意见：修正裁剪版型，把控缝制尺度，全数复测尺寸，剔除不合格品。",
        en: "Inspection overview: Measured key dimensions such as garment length, chest circumference, and sleeve length do not match the drawing standard parameters in multiple places. Dimension variation between pieces is excessive and exceeds the allowable tolerance range.\nJudgment standard: Pattern dimensions do not meet the standard and may cause poor fit or distorted wearing silhouette.\nCorrective action: Correct the cutting pattern, control sewing dimensions, remeasure all sizes, and remove nonconforming items.",
        ja: "検査概況：着丈、胸囲、袖丈などの主要寸法を実測したところ、複数箇所で図面の標準パラメータと一致せず、個体間の寸法誤差が大きく、公差許容範囲を超えています。\n判定基準：型紙寸法が基準を満たしておらず、着用時にシルエットが崩れる可能性があります。\n是正意見：裁断型紙を修正し、縫製寸法を管理し、全数の寸法を再測定して不合格品を除外してください。",
        ko: "검사 개요: 실제 측정한 총장, 가슴둘레, 소매길이 등 주요 치수가 여러 곳에서 도면 표준 파라미터와 맞지 않으며, 개별 제품 간 치수 오차가 크고 허용 공차 범위를 초과했습니다.\n판정 기준: 패턴 치수가 기준에 미달하여 착용 시 핏이 변형될 가능성이 있습니다.\n개선 의견: 재단 패턴을 수정하고 봉제 치수를 관리하며, 전수 치수 재측정 후 불합격품을 제외해야 합니다.",
        ar: "نظرة عامة على الفحص: القياسات الفعلية للأبعاد الرئيسية مثل طول الثوب ومحيط الصدر وطول الأكمام لا تتطابق في عدة مواضع مع المعايير المحددة في الرسم، كما أن اختلاف المقاسات بين القطع كبير ويتجاوز نطاق السماحية المسموح به.\nمعيار الحكم: أبعاد الباترون غير مطابقة للمعيار، وقد تؤدي إلى تشوه شكل اللباس عند الارتداء.\nإجراء التصحيح: تعديل باترون القص، وضبط مقاسات الخياطة، وإعادة قياس جميع المقاسات، واستبعاد المنتجات غير المطابقة.",
        es: "Resumen de inspección: Las medidas reales de dimensiones clave como largo de prenda, contorno de pecho y largo de manga no coinciden en varios puntos con los parámetros estándar del plano. La variación de tamaño entre piezas es elevada y supera el rango de tolerancia permitido.\nCriterio de evaluación: Las dimensiones del patrón no cumplen con el estándar y pueden causar deformación del ajuste al usar la prenda.\nAcción correctiva: Corregir el patrón de corte, controlar las dimensiones de costura, volver a medir todas las tallas y retirar las piezas no conformes.",
        ru: "Обзор проверки: Фактические измерения ключевых размеров, включая длину изделия, обхват груди и длину рукава, в нескольких местах не соответствуют стандартным параметрам чертежа. Отклонения размеров между отдельными изделиями слишком велики и превышают допустимый интервал.\nКритерий оценки: Размеры лекала не соответствуют стандарту и могут привести к искажению посадки при носке.\nКорректирующие меры: Исправить лекало раскроя, контролировать размеры при пошиве, повторно измерить все изделия и исключить несоответствующую продукцию."
      },
      updatedAt: "2026-05-23 09:10"
    })
  ];

  var flowSteps = [
    { key: "created", title: "发起问题", desc: "填写问题、图片和处理人" },
    { key: "todo", title: "处理人处理", desc: "处理、完结或转交" },
    { key: "waiting_customer", title: "等待客户回复", desc: "客户确认处理结果" },
    { key: "customer_replied", title: "同步客户信息", desc: "翻译并同步内部" },
    { key: "closed", title: "完结工单", desc: "同步结果并完结" }
  ];

  var stateMeta = {
    todo: {
      label: "待处理",
      tag: "blue",
      flow: 2,
      next: "处理人填写意见，或转交/完结工单"
    },
    waiting_customer: {
      label: "待客户确认",
      tag: "orange",
      flow: 3,
      next: "等待客户回复，收到后同步客户信息"
    },
    customer_replied: {
      label: "客户已回复",
      tag: "green",
      flow: 4,
      next: "翻译客户内容并同步给提出人和处理人"
    },
    customer_confirmed: {
      label: "客户已确认",
      tag: "green",
      flow: 5,
      next: "客户信息已同步，发起人可完结工单"
    },
    closed: {
      label: "已完结",
      tag: "gray",
      flow: 5,
      next: "只可查看"
    }
  };

  var products = [
    {
      id: "p1",
      shop: "万亨畜牧用品",
      platform: "淘",
      name: "鹦鹉奶粉喂食工具套装",
      image: "cup",
      itemId: "D000005171",
      sku: "20260517",
      asin: "080119ASIN",
      country: "Korea",
      business: "唐芬芬",
      purchase: "包瑞楠",
      color: "白色",
      size: "3件套",
      statusText: "待检品",
      attr: "颜色分类：超值装3个；喂奶勺",
      price: "5.07",
      count: 4,
      amount: "20.28",
      quantities: { buy: 4, arrive: 4, check: 4, good: "--", pending: 1, normal: "--" },
      fees: [
        ["原商品金额", "¥20.28"],
        ["变化金额", "¥20.28"],
        ["实际支出", "---"],
        ["正品金额", "¥0.00"],
        ["国内运费", "---"],
        ["到付运费", "---"],
        ["退换货运费", "¥0.00"],
        ["采购差价", "¥0.00"],
        ["优惠金额", "---"]
      ]
    },
    {
      id: "p2",
      shop: "芸祥商贸",
      platform: "1688",
      name: "仓鼠垫料除臭颗粒",
      image: "jar",
      itemId: "D000005170",
      sku: "---",
      asin: "---",
      country: "Korea",
      business: "唐芬芬",
      purchase: "包瑞楠",
      color: "蓝风铃香味",
      size: "1200ml",
      statusText: "待采购",
      attr: "规格：桶装【1200ml】；蓝风铃香味",
      price: "4.70",
      count: 1,
      amount: "4.70",
      quantities: { buy: "--", arrive: "--", check: "--", good: "--", pending: 1, normal: "--" },
      fees: [
        ["原商品金额", "¥4.70"],
        ["实际支出", "---"],
        ["退换货运费", "¥0.00"],
        ["优惠金额", "---"]
      ]
    }
  ];

  function uid(prefix) {
    return prefix + Math.random().toString(36).slice(2, 9);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function cleanupLegacyStorage() {
    try {
      LEGACY_STORAGE_KEYS.forEach(function (key) {
        localStorage.removeItem(key);
      });
    } catch (error) {
      console.warn("Failed to clean legacy workorder demo data:", error);
    }
  }

  function compactImageForStorage(image) {
    if (!image || typeof image !== "object") return image;
    var next = Object.assign({}, image);
    if (typeof next.url === "string" && next.url.indexOf("data:") === 0) {
      next.url = "";
      next.storageNote = "local-preview-removed";
    }
    return next;
  }

  function compactStoreForStorage(store) {
    var next = JSON.parse(
      JSON.stringify(store, function (key, value) {
        if (key === "url" && typeof value === "string" && value.indexOf("data:") === 0) return "";
        return value;
      })
    );
    var imageFields = [
      "images",
      "physicalImages",
      "linkImages",
      "customerImages",
      "customerPhysicalImages",
      "customerLinkImages",
      "handlerImages",
      "closeImages"
    ];
    (next.tickets || []).forEach(function (ticket) {
      imageFields.forEach(function (field) {
        if (Array.isArray(ticket[field])) {
          ticket[field] = ticket[field].map(compactImageForStorage);
        }
      });
      (ticket.records || []).forEach(function (record) {
        if (Array.isArray(record.images)) record.images = record.images.map(compactImageForStorage);
      });
      (ticket.conversations || []).forEach(function (message) {
        if (Array.isArray(message.images)) message.images = message.images.map(compactImageForStorage);
      });
    });
    return next;
  }

  function imageStub(name, theme) {
    return { id: uid("img_"), name: name, theme: theme || "cup", url: "" };
  }

  function selectedImages(images) {
    return clone(images || []).map(function (image) {
      image.selected = image.selected !== false;
      return image;
    });
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function currentTimeText() {
    var now = new Date();
    return (
      now.getFullYear() +
      "-" +
      pad2(now.getMonth() + 1) +
      "-" +
      pad2(now.getDate()) +
      " " +
      pad2(now.getHours()) +
      ":" +
      pad2(now.getMinutes())
    );
  }

  function fallbackCreatedAt(ticket) {
    var logs = Array.isArray(ticket.logs) ? ticket.logs : [];
    var createdLog = logs.find(function (log) {
      return log && log.action === "发起工单" && log.time && log.time !== "刚刚";
    });
    return createdLog ? createdLog.time : currentTimeText();
  }

  function makeTicket(config) {
    var baseImages = config.images || [imageStub("商品问题图 1", "cup"), imageStub("商品问题图 2", "bag")];
    var physicalImages = config.physicalImages || baseImages;
    var linkImages = config.linkImages || [];
    var allImages = config.images || physicalImages.concat(linkImages);
    var ticket = {
      id: config.id,
      productId: config.productId || "p1",
      orderNo: config.orderNo || ORDER_NO,
      customerNo: config.customerNo || CUSTOMER_NO,
      stage: config.stage || "todo",
      proposer: config.proposer || DEMO_PROPOSER,
      currentHandler: config.currentHandler || "采购 包瑞楠",
      templateId: config.templateId || "",
      issueText:
        config.issueText ||
        "质检发现商品边缘有轻微划痕，不影响正常使用。请确认是否可以继续发货，并保留客户回复作为后续发货依据。",
      images: allImages,
      physicalImages: physicalImages,
      linkImages: linkImages,
      customerPhysicalImages: config.customerPhysicalImages || selectedImages(physicalImages).map(function (image) {
        return markCustomerImage(image, "physical");
      }),
      customerLinkImages: config.customerLinkImages || selectedImages(linkImages).map(function (image) {
        return markCustomerImage(image, "link");
      }),
      customerImages: config.customerImages || selectedImages(allImages),
      handlerImages: config.handlerImages || [],
      handlerOpinion: config.handlerOpinion || "",
      customerText: config.customerText || "",
      customerFollowText: config.customerFollowText || "",
      replyChoice: config.replyChoice || "",
      replyOriginal: config.replyOriginal || "",
      replyTranslation: config.replyTranslation || "",
      syncTargets: config.syncTargets || [],
      closeResult: config.closeResult || "",
      closeImages: config.closeImages || [],
      source: config.source || "订单详情商品行",
      createdAt: config.createdAt || "2026-05-21 09:12",
      logs: config.logs || [],
      records: config.records || [],
      conversations: config.conversations || []
    };

    if (!ticket.logs.length) {
      ticket.logs.push({
        time: ticket.createdAt,
        actor: ticket.proposer,
        action: "发起工单",
        detail: "提交商品问题，并指定处理人：" + ticket.currentHandler
      });
    }
    return ticket;
  }

  function seedStore() {
    return {
      version: STORAGE_VERSION,
      activeProductId: "p1",
      activeTicketId: "",
      templateCounter: 3,
      issueTemplates: clone(defaultIssueTemplates),
      tickets: []
    };
  }

  function normalizeStore(store) {
    if (!store || !Array.isArray(store.tickets)) return seedStore();
    var shouldResetTemplates = !Array.isArray(store.issueTemplates) || (store.version || 0) < 6;
    if (shouldResetTemplates) store.issueTemplates = clone(defaultIssueTemplates);
    store.issueTemplates = store.issueTemplates.map(function (template, index) {
      var translations = Object.assign(emptyTranslations(), template.translations || {});
      return {
        id: template.id || "tpl_" + index,
        name: template.name || "未命名模板",
        enabled: template.enabled !== false,
        translations: translations,
        updatedAt: template.updatedAt || "刚刚"
      };
    });
    if (!store.templateCounter || shouldResetTemplates) store.templateCounter = store.issueTemplates.length + 1;
    normalizeTicketIds(store);
    store.tickets.forEach(function (ticket) {
      ticket.stage = normalizeStage(ticket.stage);
      ticket.proposer = remapDemoPerson(ticket.proposer);
      ticket.currentHandler = remapDemoPerson(ticket.currentHandler);
      if (typeof ticket.replyTranslation !== "string") ticket.replyTranslation = "";
      if (typeof ticket.templateId !== "string") ticket.templateId = "";
      if (!Array.isArray(ticket.syncTargets)) ticket.syncTargets = [];
      ticket.syncTargets = ticket.syncTargets.map(remapDemoPerson);
      if (!Array.isArray(ticket.handlerImages)) ticket.handlerImages = [];
      if (!Array.isArray(ticket.closeImages)) ticket.closeImages = [];
      if (!Array.isArray(ticket.linkImages)) ticket.linkImages = [];
      if (!Array.isArray(ticket.physicalImages)) ticket.physicalImages = [];
      if (!Array.isArray(ticket.customerPhysicalImages)) ticket.customerPhysicalImages = [];
      if (!Array.isArray(ticket.customerLinkImages)) ticket.customerLinkImages = [];
      if (!Array.isArray(ticket.conversations)) ticket.conversations = [];
      ticket.conversations = normalizeConversationsList(ticket.conversations);
      ticket.conversations.forEach(function (message) {
        if (!message) return;
        message.actor = remapDemoPerson(message.actor);
        message.text = replaceDemoPersonText(message.text);
      });
      if (!ticket.orderNo) ticket.orderNo = ORDER_NO;
      if (!ticket.customerNo) ticket.customerNo = CUSTOMER_NO;
      if (!ticket.createdAt) ticket.createdAt = fallbackCreatedAt(ticket);
      cleanDeadlineContent(ticket);
      if (Array.isArray(ticket.logs)) {
        ticket.logs.forEach(function (log) {
          if (!log) return;
          log.actor = remapDemoPerson(log.actor);
          log.detail = replaceDemoPersonText(log.detail);
        });
        var createdLog = ticket.logs.find(function (log) {
          return log && log.action === "发起工单";
        });
        if (createdLog && (!createdLog.time || createdLog.time === "刚刚")) createdLog.time = ticket.createdAt;
      }
      if (Array.isArray(ticket.records)) {
        ticket.records.forEach(function (record) {
          if (!record) return;
          record.actor = remapDemoPerson(record.actor);
          record.to = replaceDemoPersonText(record.to);
          record.content = replaceDemoPersonText(record.content);
        });
      }
      if (!ticket.physicalImages.length && !ticket.linkImages.length) ticket.physicalImages = clone(ticket.images || []);
      ensureCustomerImageBuckets(ticket);
    });
    store.version = STORAGE_VERSION;
    return store;
  }

  function loadStore() {
    try {
      cleanupLegacyStorage();
      var stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return seedStore();
      if (stored.length > 2000000) {
        console.warn("Stored workorder demo data is too large, using seed data.");
        return seedStore();
      }
      
      var cached = JSON.parse(stored);
      
      if (!cached || typeof cached !== "object") {
        return seedStore();
      }
      
      if (!Array.isArray(cached.tickets) || cached.tickets.length > 100) {
        return seedStore();
      }
      
      for (var i = 0; i < cached.tickets.length; i++) {
        var ticket = cached.tickets[i];
        if (!ticket || typeof ticket !== "object" || !ticket.id) {
          return seedStore();
        }
      }
      
      return normalizeStore(cached);
    } catch (error) {
      console.warn("Failed to load store from localStorage, using seed data:", error);
      return seedStore();
    }
  }

  function saveStore(store) {
    try {
      var compactStore = compactStoreForStorage(store);
      var payload = JSON.stringify(compactStore);
      if (payload.length > 1200000) {
        console.warn("Workorder demo data is too large, saving seed data instead.");
        payload = JSON.stringify(seedStore());
      }
      localStorage.setItem(STORAGE_KEY, payload);
    } catch (error) {
      console.warn("Failed to save workorder demo data:", error);
    }
  }

  function findProduct(id) {
    return products.find(function (item) {
      return item.id === id;
    }) || products[0];
  }

  function escapeRegExp(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function ticketSequenceFromId(id, productId) {
    var value = String(id || "");
    var match = value.match(/^(\d+)$/);
    if (match) return Number(match[1]);
    var itemId = findProduct(productId).itemId;
    var escapedItemId = escapeRegExp(itemId);
    match = value.match(new RegExp("^(\\d+)-" + escapedItemId + "$"));
    if (match) return Number(match[1]);
    match = value.match(new RegExp("^DD-GD-" + escapedItemId + "-(\\d+)$"));
    return match ? Number(match[1]) : 0;
  }

  function formatTicketId(productId, sequence) {
    return String(sequence).padStart(3, "0");
  }

  function isCurrentTicketId(id, productId) {
    var sequence = ticketSequenceFromId(id, productId);
    return sequence > 0 && String(id || "") === formatTicketId(productId, sequence);
  }

  function normalizeTicketIds(store) {
    var maxSequence = 0;
    var usedSequences = {};
    var idMap = {};
    store.tickets.forEach(function (ticket) {
      var productId = ticket.productId || "p1";
      var sequence = ticketSequenceFromId(ticket.id, productId);
      if (sequence) maxSequence = Math.max(maxSequence, sequence);
    });
    store.tickets.forEach(function (ticket) {
      ticket.productId = ticket.productId || "p1";
      var sequence = ticketSequenceFromId(ticket.id, ticket.productId);
      var currentId = isCurrentTicketId(ticket.id, ticket.productId);
      if (!sequence || usedSequences[sequence]) {
        maxSequence += 1;
        sequence = maxSequence;
      }
      usedSequences[sequence] = true;
      if (currentId && String(ticket.id || "") === formatTicketId(ticket.productId, sequence)) return;
      var oldId = ticket.id;
      ticket.id = formatTicketId(ticket.productId, sequence);
      if (oldId) idMap[oldId] = ticket.id;
    });
    if (idMap[store.activeTicketId]) store.activeTicketId = idMap[store.activeTicketId];
    if (
      store.activeTicketId &&
      !store.tickets.some(function (ticket) {
        return ticket.id === store.activeTicketId;
      })
    ) {
      store.activeTicketId = "";
    }
    if (!store.activeTicketId && store.tickets[0]) store.activeTicketId = store.tickets[0].id;
  }

  function nextTicketId(store, productId) {
    var maxSequence = (store.tickets || []).reduce(function (max, ticket) {
      return Math.max(max, ticketSequenceFromId(ticket.id, ticket.productId || productId || "p1"));
    }, 0);
    return formatTicketId(productId, maxSequence + 1);
  }

  function customerLanguageKey(productId) {
    var product = findProduct(productId);
    var country = String(product.country || "").toLowerCase();
    if (country.indexOf("japan") >= 0) return "ja";
    if (country.indexOf("korea") >= 0) return "en";
    if (country.indexOf("arab") >= 0 || country.indexOf("saudi") >= 0 || country.indexOf("uae") >= 0) return "ar";
    if (country.indexOf("spain") >= 0 || country.indexOf("mexico") >= 0) return "es";
    if (country.indexOf("russia") >= 0) return "ru";
    return "en";
  }

  function languageLabel(key) {
    var item = templateLanguages.find(function (language) {
      return language.key === key;
    });
    return item ? item.label : "中文";
  }

  function templateText(template, languageKey) {
    if (!template || !template.translations) return "";
    return template.translations[languageKey] || template.translations.zh || "";
  }

  function defaultNewTicket(productId) {
    return {
      productId: productId || "p1",
      handler: "采购 包瑞楠",
      templateId: "",
      issueText: "",
      physicalImages: [],
      linkImages: []
    };
  }

  function defaultTemplateForm(template) {
    if (template) return clone(template);
    return makeIssueTemplate({
      id: "",
      name: "",
      enabled: true,
      translations: emptyTranslations()
    });
  }

  function tagClass(stage) {
    var meta = stateMeta[normalizeStage(stage)] || stateMeta.todo;
    return "tag " + (meta.tag || "");
  }

  function normalizeStage(stage) {
    if (stage === "business_review") return "todo";
    return stateMeta[stage] ? stage : "todo";
  }

  function summaryText(ticket) {
    return String(ticket.issueText || "").replace(/\s+/g, " ").slice(0, 48);
  }

  function stripDeadlineText(value) {
    if (typeof value !== "string") return value;
    var label = "处理" + "时限：";
    var escapedLabel = escapeRegExp(label);
    return value
      .replace(new RegExp("\\n?" + escapedLabel + "[^，。\\n]*(?=[，。\\n]|$)", "g"), "")
      .replace(new RegExp("，" + escapedLabel + "[^，。\\n]*", "g"), "")
      .replace(new RegExp(escapedLabel + "[^，。\\n]*(，)?", "g"), "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function cleanDeadlineContent(ticket) {
    delete ticket.deadlineHours;
    ["issueText", "handlerOpinion", "customerText", "customerFollowText", "closeResult"].forEach(function (key) {
      ticket[key] = stripDeadlineText(ticket[key]);
    });
    (ticket.records || []).forEach(function (record) {
      record.content = stripDeadlineText(record.content);
    });
    (ticket.logs || []).forEach(function (log) {
      log.detail = stripDeadlineText(log.detail);
    });
  }

  function remapDemoPerson(person) {
    return person === LEGACY_DEMO_PROPOSER ? DEMO_PROPOSER : person;
  }

  function replaceDemoPersonText(value) {
    if (typeof value !== "string") return value;
    return value.split(LEGACY_DEMO_PROPOSER).join(DEMO_PROPOSER);
  }

  function addLog(ticket, actor, action, detail) {
    ticket.logs.push({
      time: "刚刚",
      actor: actor || CURRENT_USER,
      action: action,
      detail: detail || ""
    });
  }

  function ensureRecords(ticket) {
    if (!Array.isArray(ticket.records)) ticket.records = [];
    return ticket.records;
  }

  function addRecord(ticket, actor, action, content, to, images) {
    ensureRecords(ticket).push({
      time: "刚刚",
      actor: actor,
      action: action,
      content: content || "未填写补充说明。",
      to: to || "",
      images: clone(images || [])
    });
  }

  function conversationKey(message) {
    return [message.from || "", message.actor || "", message.choice || "", message.text || ""].join("||");
  }

  function normalizeConversationsList(conversations) {
    var indexMap = {};
    var result = [];
    (conversations || []).forEach(function (message) {
      var key = conversationKey(message);
      if (Object.prototype.hasOwnProperty.call(indexMap, key)) {
        result[indexMap[key]] = message;
      } else {
        indexMap[key] = result.length;
        result.push(message);
      }
    });
    return result;
  }

  function imageIdMap(images) {
    var map = {};
    (images || []).forEach(function (image) {
      if (image && image.id) map[image.id] = true;
    });
    return map;
  }

  function markCustomerImage(image, group) {
    if (!image) return image;
    var nextGroup = group || image.customerGroup || "physical";
    if (image.customerGroup !== nextGroup) image.customerGroup = nextGroup;
    if (image.selected === undefined) image.selected = true;
    return image;
  }

  function sameImageRefs(left, right) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
    for (var i = 0; i < left.length; i++) {
      if (!left[i] || !right[i] || left[i].id !== right[i].id || left[i].customerGroup !== right[i].customerGroup) return false;
    }
    return true;
  }

  function ensureCustomerImageBuckets(ticket) {
    if (!ticket) return { physical: [], link: [], all: [] };
    if (
      !Array.isArray(ticket.customerPhysicalImages) ||
      !Array.isArray(ticket.customerLinkImages) ||
      (!ticket.customerBucketsReady && Array.isArray(ticket.customerImages) && ticket.customerImages.length)
    ) {
      var physicalIds = imageIdMap(ticket.physicalImages || []);
      var linkIds = imageIdMap(ticket.linkImages || []);
      var source = Array.isArray(ticket.customerImages) && ticket.customerImages.length ? ticket.customerImages : [];
      var physical = [];
      var link = [];

      if (source.length) {
        source.forEach(function (image) {
          var group = image.customerGroup || image.group || (linkIds[image.id] ? "link" : "physical");
          if (!physicalIds[image.id] && !linkIds[image.id] && group !== "link") group = "physical";
          (group === "link" ? link : physical).push(markCustomerImage(image, group));
        });
      } else {
        physical = selectedImages(ticket.physicalImages && ticket.physicalImages.length ? ticket.physicalImages : ticket.images || []).map(function (image) {
          return markCustomerImage(image, "physical");
        });
        link = selectedImages(ticket.linkImages || []).map(function (image) {
          return markCustomerImage(image, "link");
        });
      }

      ticket.customerPhysicalImages = physical;
      ticket.customerLinkImages = link;
      ticket.customerBucketsReady = true;
    }

    (ticket.customerPhysicalImages || []).forEach(function (image) {
      markCustomerImage(image, "physical");
    });
    (ticket.customerLinkImages || []).forEach(function (image) {
      markCustomerImage(image, "link");
    });
    var allImages = (ticket.customerPhysicalImages || []).concat(ticket.customerLinkImages || []);
    if (!sameImageRefs(ticket.customerImages, allImages)) ticket.customerImages = allImages;
    if (!ticket.customerBucketsReady) ticket.customerBucketsReady = true;
    return {
      physical: ticket.customerPhysicalImages,
      link: ticket.customerLinkImages,
      all: allImages
    };
  }

  function ensureCustomerImages(ticket) {
    return ensureCustomerImageBuckets(ticket).all;
  }

  function imagesByCustomerGroup(images, group) {
    return (images || []).filter(function (image) {
      var imageGroup = image.customerGroup || image.group || "physical";
      return group === "link" ? imageGroup === "link" : imageGroup !== "link";
    });
  }

  function ensureConversations(ticket) {
    if (!ticket) return [];
    var source = Array.isArray(ticket.conversations) ? ticket.conversations : [];
    var next = source;
    var changed = !Array.isArray(ticket.conversations);
    if (!next.length && ticket.customerText) {
      next = next.slice();
      next.push({
        id: uid("msg_"),
        time: "2026-05-21 09:40",
        from: "业务",
        actor: BUSINESS_HANDLER,
        text: ticket.customerText,
        images: ensureCustomerImages(ticket).filter(function (image) {
          return image.selected !== false;
        })
      });
      changed = true;
    }
    if (
      ticket.replyOriginal &&
      !next.some(function (message) {
        return message.from === "客户" && message.text === ticket.replyOriginal;
      })
    ) {
      next = next.slice();
      next.push({
        id: uid("msg_"),
        time: "2026-05-21 10:18",
        from: "客户",
        actor: "客户",
        choice: ticket.replyChoice,
        text: ticket.replyOriginal,
        images: []
      });
      changed = true;
    }
    var normalized = normalizeConversationsList(next);
    if (normalized.length !== next.length) changed = true;
    if (changed) ticket.conversations = normalized;
    return ticket.conversations;
  }

  function addConversation(ticket, from, actor, text, images, choice) {
    if (!Array.isArray(ticket.conversations)) ticket.conversations = [];
    ticket.conversations.push({
      id: uid("msg_"),
      time: "刚刚",
      from: from,
      actor: actor,
      choice: choice || "",
      text: text || "",
      images: clone(images || [])
    });
    ticket.conversations = normalizeConversationsList(ticket.conversations);
  }

  function latestCustomerMessage(ticket) {
    var messages = ensureConversations(ticket).filter(function (message) {
      return message.from === "客户";
    });
    return messages[messages.length - 1] || null;
  }

  function historyTimeValue(time) {
    if (time === "刚刚") return Number.MAX_SAFE_INTEGER;
    var value = String(time || "").replace(/-/g, "/");
    var parsed = new Date(value).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function dateRangeValue(date, endOfDay) {
    if (!date) return 0;
    var suffix = endOfDay ? " 23:59:59" : " 00:00:00";
    var parsed = new Date(String(date).replace(/-/g, "/") + suffix).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function normalizeSpecText(value) {
    return String(value || "")
      .replace(/\s+/g, "")
      .replace(/[，,；;]/g, "|")
      .toLowerCase();
  }

  function productSpecKey(product) {
    var item = product || {};
    return [item.name, item.color, item.size, item.attr].map(normalizeSpecText).join("::");
  }

  function buildApp(pageType) {
    return {
      data: function () {
        return {
          orderNo: ORDER_NO,
          customerNo: CUSTOMER_NO,
          currentUser: CURRENT_USER,
          businessHandler: BUSINESS_HANDLER,
          products: products,
          people: people,
          templateLanguages: templateLanguages,
          flowSteps: flowSteps,
          store: loadStore(),
          drawerOpen: false,
          drawerMinimized: false,
          createOpen: false,
          createMinimized: false,
          activeTab: "handle",
          activeFilter: "mine",
          workbenchMode: "todo",
          searchOrder: ORDER_NO,
          customerQuery: "",
          filterStage: "all",
          filterHandler: "all",
          filterDateStart: "",
          filterDateEnd: "",
          newTicket: defaultNewTicket("p1"),
          createHistoryFilter: { customerNo: "", orderNo: "", templateId: "" },
          detailHistoryFilter: { customerNo: "", orderNo: "", templateId: "" },
          actionMode: "process",
          transferForm: { to: "", reason: "", images: [] },
          closeForm: { opinion: "", images: [] },
          replyForm: { choice: "可以接受", original: "" },
          followupForm: { text: "" },
          previewImage: null,
          selectedTicketId: "",
          toast: "",
          showAllRecords: false,
          infoTab: "all",
          highlightedHistoryKey: "",
          activeTemplateLang: "zh",
          templateSearch: "",
          templateEditingId: "",
          issueTemplateForm: defaultTemplateForm()
        };
      },
      computed: {
        tickets: function () {
          return this.store.tickets;
        },
        issueTemplates: function () {
          return this.store.issueTemplates || [];
        },
        enabledIssueTemplates: function () {
          return this.issueTemplates.filter(function (template) {
            return template.enabled !== false;
          });
        },
        activeIssueTemplate: function () {
          var id = this.newTicket.templateId;
          return this.issueTemplates.find(function (template) {
            return template.id === id;
          }) || null;
        },
        newTicketLanguageKey: function () {
          return "zh";
        },
        filteredIssueTemplates: function () {
          var keyword = this.templateSearch.trim();
          if (!keyword) return this.issueTemplates;
          return this.issueTemplates.filter(function (template) {
            return (
              template.name.indexOf(keyword) >= 0 ||
              String(template.translations.zh || "").indexOf(keyword) >= 0 ||
              String(template.translations.en || "").toLowerCase().indexOf(keyword.toLowerCase()) >= 0
            );
          });
        },
        currentProduct: function () {
          return findProduct(this.store.activeProductId);
        },
        currentTickets: function () {
          var productId = this.currentProduct.id;
          return this.tickets.filter(function (ticket) {
            return ticket.productId === productId;
          });
        },
        currentTicket: function () {
          var active = this.tickets.find(
            function (ticket) {
              return ticket.id === this.store.activeTicketId;
            }.bind(this)
          );
          if (active) return active;
          return this.currentTickets[0] || null;
        },
        openCount: function () {
          return this.tickets.filter(function (ticket) {
            return ticket.stage !== "closed";
          }).length;
        },
        myPendingCount: function () {
          return this.tickets.filter(
            function (ticket) {
              return ticket.stage !== "closed" && ticket.currentHandler === this.currentUser;
            }.bind(this)
          ).length;
        },
        workbenchTabs: function () {
          var tickets = this.tickets;
          var scopedTickets = tickets.filter(
            function (ticket) {
              return this.workbenchMode === "history" || this.isWorkbenchRelatedTicket(ticket);
            }.bind(this)
          );
          if (this.workbenchMode === "history") {
            return [
              {
                key: "todo",
                label: "待处理",
                count: scopedTickets.filter(function (ticket) {
                  return ticket.stage === "todo";
                }).length
              },
              {
                key: "waiting_customer",
                label: "待客户确认",
                count: scopedTickets.filter(function (ticket) {
                  return ticket.stage === "waiting_customer";
                }).length
              },
              {
                key: "customer_replied",
                label: "客户已回复",
                count: scopedTickets.filter(function (ticket) {
                  return ticket.stage === "customer_replied";
                }).length
              },
              {
                key: "customer_confirmed",
                label: "客户已确认",
                count: scopedTickets.filter(function (ticket) {
                  return ticket.stage === "customer_confirmed";
                }).length
              },
              {
                key: "closed",
                label: "已完结",
                count: scopedTickets.filter(function (ticket) {
                  return ticket.stage === "closed";
                }).length
              },
              { key: "all", label: "全部", count: scopedTickets.length }
            ];
          }
          return [
            {
              key: "mine",
              label: "待我处理",
              count: scopedTickets.filter(
                function (ticket) {
                  return ticket.stage !== "closed" && ticket.currentHandler === this.currentUser;
                }.bind(this)
              ).length
            },
            {
              key: "created_by_me",
              label: "我发起的",
              count: scopedTickets.filter(
                function (ticket) {
                  return this.samePerson(ticket.proposer, DEMO_PROPOSER);
                }.bind(this)
              ).length
            },
            {
              key: "todo",
              label: "待处理",
              count: scopedTickets.filter(function (ticket) {
                return ticket.stage === "todo";
              }).length
            },
            {
              key: "waiting_customer",
              label: "待客户确认",
              count: scopedTickets.filter(function (ticket) {
                return ticket.stage === "waiting_customer";
              }).length
            },
            {
              key: "customer_replied",
              label: "客户已回复",
              count: scopedTickets.filter(function (ticket) {
                return ticket.stage === "customer_replied";
              }).length
            },
            {
              key: "customer_confirmed",
              label: "客户已确认",
              count: scopedTickets.filter(function (ticket) {
                return ticket.stage === "customer_confirmed";
              }).length
            },
            {
              key: "closed",
              label: "已完结",
              count: scopedTickets.filter(function (ticket) {
                return ticket.stage === "closed";
              }).length
            },
            { key: "all", label: "全部", count: scopedTickets.length }
          ];
        },
        filteredTickets: function () {
          var self = this;
          return this.tickets.filter(function (ticket) {
            if (self.workbenchMode !== "history" && !self.isWorkbenchRelatedTicket(ticket)) return false;
            if (self.activeFilter === "mine" && (ticket.stage === "closed" || ticket.currentHandler !== self.currentUser)) return false;
            if (self.activeFilter === "created_by_me" && !self.samePerson(ticket.proposer, DEMO_PROPOSER)) return false;
            if (
              ["todo", "waiting_customer", "customer_replied", "customer_confirmed", "closed"].indexOf(self.activeFilter) >= 0 &&
              ticket.stage !== self.activeFilter
            ) {
              return false;
            }
            if (self.filterStage !== "all" && ticket.stage !== self.filterStage) return false;
            if (self.filterHandler !== "all" && ticket.currentHandler !== self.filterHandler) return false;
            var start = dateRangeValue(self.filterDateStart, false);
            var end = dateRangeValue(self.filterDateEnd, true);
            var createdValue = historyTimeValue(ticket.createdAt);
            if (start && createdValue < start) return false;
            if (end && createdValue > end) return false;
            var customerKeyword = self.customerQuery.trim();
            if (customerKeyword && self.customerNoOf(ticket).indexOf(customerKeyword) < 0) return false;
            var keyword = self.searchOrder.trim();
            if (keyword) {
              var product = findProduct(ticket.productId);
              var searchable = [self.orderNoOf(ticket), self.customerNoOf(ticket), ticket.id, product.itemId, product.name].join(" ");
              if (searchable.indexOf(keyword) < 0) return false;
            }
            return true;
          });
        },
        selectedTicket: function () {
          if (!this.selectedTicketId) return null;
          return (
            this.tickets.find(
              function (ticket) {
                return ticket.id === this.selectedTicketId;
              }.bind(this)
            ) || null
          );
        }
      },
      watch: {
        "newTicket.handler": function () {
          if (this.newTicket.templateId) this.applyIssueTemplate();
        },
        "newTicket.templateId": function (value) {
          if (value) this.applyIssueTemplate();
        }
      },
      mounted: function () {
        this.syncFromQuery(pageType);
        if (pageType === "templates" && this.issueTemplates.length) {
          this.editIssueTemplate(this.issueTemplates[0]);
        }
      },
      methods: {
        save: function () {
          saveStore(this.store);
        },
        stateMeta: function (stage) {
          return stateMeta[normalizeStage(stage)] || stateMeta.todo;
        },
        tagClass: tagClass,
        historyEntryTagClass: function (kind) {
          if (kind === "internal") return "blue";
          if (kind === "customer") return "green";
          return "gray";
        },
        summaryText: summaryText,
        productById: findProduct,
        productSpecKey: productSpecKey,
        orderNoOf: function (ticket) {
          return (ticket && ticket.orderNo) || ORDER_NO;
        },
        otherOrderNoOf: function (ticket, index) {
          var orderNo = this.orderNoOf(ticket);
          if (orderNo !== ORDER_NO) return orderNo;
          return "B2B-DD-KOR8-260517-" + String(145 + (Number(index) || 0)).padStart(3, "0");
        },
        customerNoOf: function (ticket) {
          return (ticket && ticket.customerNo) || CUSTOMER_NO;
        },
        sameSpecTickets: function (productId, excludeTicketId) {
          var currentProduct = findProduct(productId);
          var currentKey = productSpecKey(currentProduct);
          return this.tickets
            .filter(function (ticket) {
              if (excludeTicketId && ticket.id === excludeTicketId) return false;
              return productSpecKey(findProduct(ticket.productId)) === currentKey;
            })
            .sort(function (a, b) {
              return historyTimeValue(b.createdAt) - historyTimeValue(a.createdAt);
            });
        },
        sameSpecTicketsFiltered: function (productId, excludeTicketId, filter) {
          var self = this;
          var customerKeyword = String((filter && filter.customerNo) || "").trim();
          var orderKeyword = String((filter && filter.orderNo) || "").trim();
          var templateId = String((filter && filter.templateId) || "");
          return this.sameSpecTickets(productId, excludeTicketId).filter(function (ticket, index) {
            var visibleOrderNo = self.otherOrderNoOf(ticket, index);
            if (customerKeyword && self.customerNoOf(ticket).indexOf(customerKeyword) < 0) return false;
            if (orderKeyword && self.orderNoOf(ticket).indexOf(orderKeyword) < 0 && visibleOrderNo.indexOf(orderKeyword) < 0) return false;
            if (templateId === "__custom__" && ticket.templateId) return false;
            if (templateId && templateId !== "__custom__" && ticket.templateId !== templateId) return false;
            return true;
          });
        },
        openSameSpecTicket: function (ticket) {
          if (!ticket) return;
          var url =
            "代购订单详情.html?ticket=" +
            encodeURIComponent(ticket.id) +
            "&product=" +
            encodeURIComponent(ticket.productId || "");
          window.open(url, "_blank", "noopener");
        },
        languageLabel: languageLabel,
        setInfoTab: function (tab) {
          this.infoTab = tab;
          this.highlightedHistoryKey = "";
        },
        recordKey: function (record) {
          if (!record) return "";
          return ["record", record.time, record.actor, record.action, record.to, record.content].join("|");
        },
        messageKey: function (message) {
          if (!message) return "";
          return ["message", message.id || "", message.time, message.from, message.actor, message.choice, message.text].join("|");
        },
        showHistoryDetail: function (type, item) {
          if (!item) return;
          if (type === "internal") {
            this.infoTab = "internal";
            this.highlightedHistoryKey = this.recordKey(item);
          } else if (type === "customer") {
            this.infoTab = "customer";
            this.highlightedHistoryKey = this.messageKey(item);
          }
          this.$nextTick(function () {
            var node = document.querySelector(".history-focus-card");
            if (node) node.scrollIntoView({ block: "center", behavior: "smooth" });
          });
        },
        templateText: templateText,
        issueTemplateById: function (id) {
          return this.issueTemplates.find(function (template) {
            return template.id === id;
          }) || null;
        },
        issueTemplateName: function (ticket) {
          var template = this.issueTemplateById(ticket && ticket.templateId);
          return template && template.name ? template.name : "自定义内容";
        },
        templateCustomerText: function (ticket) {
          var template = this.issueTemplateById(ticket && ticket.templateId);
          return templateText(template, customerLanguageKey(ticket ? ticket.productId : "p1"));
        },
        ensureBusinessCustomerText: function (ticket) {
          if (!ticket || !this.isBusiness(ticket.currentHandler) || ticket.customerText) return;
          var text = this.templateCustomerText(ticket);
          if (text) ticket.customerText = text;
        },
        applyIssueTemplate: function () {
          if (!this.activeIssueTemplate) return;
          var text = templateText(this.activeIssueTemplate, this.newTicketLanguageKey);
          this.newTicket.issueText = text;
        },
        templateCompleteCount: function (template) {
          return templateLanguages.filter(function (language) {
            return Boolean(String((template.translations || {})[language.key] || "").trim());
          }).length;
        },
        editIssueTemplate: function (template) {
          this.templateEditingId = template ? template.id : "";
          this.issueTemplateForm = defaultTemplateForm(template || null);
          this.activeTemplateLang = "zh";
          this.toast = "";
        },
        newIssueTemplate: function () {
          this.templateEditingId = "";
          this.issueTemplateForm = defaultTemplateForm();
          this.activeTemplateLang = "zh";
          this.toast = "";
        },
        saveIssueTemplate: function () {
          var form = this.issueTemplateForm;
          if (!form.name.trim()) {
            this.toast = "请填写模板名称。";
            return;
          }
          if (!String(form.translations.zh || "").trim()) {
            this.toast = "请填写中文模板内容。";
            this.activeTemplateLang = "zh";
            return;
          }
          form.updatedAt = "刚刚";
          var index = this.issueTemplates.findIndex(
            function (template) {
              return template.id === this.templateEditingId;
            }.bind(this)
          );
          if (index >= 0) {
            this.store.issueTemplates.splice(index, 1, clone(form));
            this.toast = "模板已保存。";
          } else {
            if (!form.id) form.id = uid("tpl_");
            this.store.issueTemplates.unshift(clone(form));
            this.templateEditingId = form.id;
            this.toast = "模板已新增。";
          }
          this.save();
        },
        duplicateIssueTemplate: function (template) {
          var copy = clone(template);
          copy.id = uid("tpl_");
          copy.name = template.name + " 副本";
          copy.enabled = true;
          copy.updatedAt = "刚刚";
          this.store.issueTemplates.unshift(copy);
          this.editIssueTemplate(copy);
          this.toast = "已复制模板，可继续编辑。";
          this.save();
        },
        toggleIssueTemplate: function (template) {
          template.enabled = template.enabled === false;
          template.updatedAt = "刚刚";
          this.toast = template.enabled ? "模板已启用。" : "模板已停用。";
          this.save();
        },
        deleteIssueTemplate: function (template) {
          if (!template) return;
          if (!window.confirm("确认删除该模板？删除后创建工单中不再显示。")) return;
          var index = this.issueTemplates.findIndex(function (item) {
            return item.id === template.id;
          });
          if (index < 0) return;
          this.store.issueTemplates.splice(index, 1);
          if (this.templateEditingId === template.id) {
            if (this.issueTemplates.length) {
              this.editIssueTemplate(this.issueTemplates[0]);
            } else {
              this.newIssueTemplate();
            }
          }
          this.toast = "模板已删除。";
          this.save();
        },
        internalRecords: function (ticket) {
          return ensureRecords(ticket).slice().reverse();
        },
        allHistoryEntries: function (ticket) {
          if (!ticket) return [];
          var entries = [];
          entries.push({
            key: "issue|" + ticket.id,
            focusKey: "issue|" + ticket.id,
            kind: "issue",
            typeLabel: "工单内容",
            title: (ticket.proposer || "提出人") + " · 发起工单",
            time: ticket.createdAt || "",
            meta: "",
            templateLabel: this.issueTemplateName(ticket),
            content: ticket.issueText || "暂无问题内容。",
            physicalImages: this.physicalImages(ticket),
            linkImages: this.linkImages(ticket),
            images: []
          });

          ensureRecords(ticket).forEach(
            function (record) {
              entries.push({
                key: this.recordKey(record),
                focusKey: this.recordKey(record),
                kind: "internal",
                typeLabel: "内部处理",
                title: [record.actor, record.action].filter(Boolean).join(" · "),
                time: record.time || "",
                meta: record.to ? "转给：" + record.to : "",
                content: record.content || "",
                images: record.images || []
              });
            }.bind(this)
          );

          ensureConversations(ticket).forEach(
            function (message) {
              entries.push({
                key: this.messageKey(message),
                focusKey: this.messageKey(message),
                kind: "customer",
                typeLabel: "客户沟通",
                title: message.from === "客户" ? "客户回复" : "业务发送",
                time: message.time || "",
                meta: message.choice || (message.actor ? "发送人：" + message.actor : ""),
                content: message.text || "",
                images: message.images || []
              });
            }.bind(this)
          );

          return entries.sort(function (a, b) {
            return historyTimeValue(b.time) - historyTimeValue(a.time);
          });
        },
        visibleRecords: function (ticket) {
          var records = ensureRecords(ticket).slice().reverse();
          return this.showAllRecords ? records : records.slice(0, 3);
        },
        recordCount: function (ticket) {
          return ensureRecords(ticket).length;
        },
        customerImages: function (ticket) {
          return ensureCustomerImages(ticket);
        },
        customerPhysicalImages: function (ticket) {
          return ensureCustomerImageBuckets(ticket).physical;
        },
        customerLinkImages: function (ticket) {
          return ensureCustomerImageBuckets(ticket).link;
        },
        physicalImages: function (ticket) {
          if (!ticket) return [];
          if (Array.isArray(ticket.physicalImages) && ticket.physicalImages.length) return ticket.physicalImages;
          if (Array.isArray(ticket.linkImages) && ticket.linkImages.length) return [];
          return Array.isArray(ticket.images) ? ticket.images : [];
        },
        linkImages: function (ticket) {
          return ticket && Array.isArray(ticket.linkImages) ? ticket.linkImages : [];
        },
        selectedCustomerImages: function (ticket) {
          return ensureCustomerImages(ticket).filter(function (image) {
            return image.selected;
          });
        },
        physicalCustomerRecordImages: function (images) {
          return imagesByCustomerGroup(images, "physical");
        },
        linkCustomerRecordImages: function (images) {
          return imagesByCustomerGroup(images, "link");
        },
        conversations: function (ticket) {
          return ensureConversations(ticket).slice().reverse();
        },
        syncTargets: function (ticket) {
          var targets = [];
          function addTarget(person) {
            if (person && targets.indexOf(person) < 0) targets.push(person);
          }
          addTarget(ticket.proposer);
          ensureRecords(ticket)
            .slice()
            .reverse()
            .some(
              function (record) {
                if (record.actor && record.actor !== this.businessHandler && record.actor !== "客户") {
                  addTarget(record.actor);
                  return true;
                }
                return false;
              }.bind(this)
            );
          if (targets.length < 2 && ticket.currentHandler !== this.businessHandler) addTarget(ticket.currentHandler);
          return targets;
        },
        syncTargetText: function (ticket) {
          return this.syncTargets(ticket).join("、");
        },
        closedSyncTargets: function (ticket) {
          return ticket && ticket.syncTargets && ticket.syncTargets.length ? ticket.syncTargets : this.syncTargets(ticket);
        },
        flowLogs: function (ticket) {
          return (ticket.logs || []).slice().reverse();
        },
        latestCustomerMessage: function (ticket) {
          return latestCustomerMessage(ticket);
        },
        customerMessages: function (ticket) {
          return ensureConversations(ticket).filter(function (message) {
            return message.from === "客户";
          }).reverse();
        },
        hasCustomerReplies: function (ticket) {
          return this.customerMessages(ticket).length > 0;
        },
        latestInternalRecord: function (ticket) {
          var records = ensureRecords(ticket);
          return records.length ? records[records.length - 1] : null;
        },
        isBusiness: function (person) {
          return person === this.businessHandler;
        },
        samePerson: function (a, b) {
          if (!a || !b) return false;
          if (a === b) return true;
          var aName = String(a).trim().split(/\s+/).pop();
          var bName = String(b).trim().split(/\s+/).pop();
          return !!aName && aName === bName;
        },
        isWorkbenchRelatedTicket: function (ticket) {
          if (!ticket) return false;
          if (ticket.currentHandler === this.currentUser) return true;
          if (this.samePerson(ticket.proposer, DEMO_PROPOSER)) return true;
          return (ticket.syncTargets || []).indexOf(this.currentUser) >= 0;
        },
        canFinishTicket: function (ticket) {
          return !!ticket && (this.samePerson(ticket.proposer, this.currentUser) || this.samePerson(ticket.proposer, ticket.currentHandler));
        },
        productTickets: function (productId) {
          return this.tickets.filter(function (ticket) {
            return ticket.productId === productId;
          });
        },
        activeTickets: function (productId) {
          return this.productTickets(productId).filter(function (ticket) {
            return ticket.stage !== "closed";
          });
        },
        primaryTicket: function (productId) {
          var active = this.activeTickets(productId);
          if (active.length) return active[0];
          return this.productTickets(productId)[0] || null;
        },
        ticketStateLabel: function (ticket) {
          return this.stateMeta(ticket.stage).label;
        },
        currentOwnerText: function (ticket) {
          return ticket.currentHandler || "未指定";
        },
        nextActionLabel: function (ticket) {
          if (!ticket) return "查看";
          if (ticket.stage === "todo") return "去处理";
          if (ticket.stage === "waiting_customer") return "查看";
          if (ticket.stage === "customer_replied") return "同步客户信息";
          if (ticket.stage === "customer_confirmed") return this.canFinishTicket(ticket) ? "完结工单" : "去处理";
          return "查看";
        },
        currentNextText: function (ticket) {
          if (!ticket) return "";
          if (ticket.stage === "todo" && this.isBusiness(ticket.currentHandler)) {
            return "业务可发送客户确认，也可转交给其他处理人";
          }
          return this.stateMeta(ticket.stage).next;
        },
        flowClass: function (index, ticket) {
          if (!ticket) return "";
          var stage = normalizeStage(ticket.stage);
          var flow = this.stateMeta(stage).flow;
          if (stage === "closed") flow = flowSteps.length;
          if (index < flow) return "is-done";
          if (index === flow) return "is-current";
          return "";
        },
        syncFromQuery: function (pageType) {
          var params = new URLSearchParams(window.location.search);
          var ticketId = params.get("ticket");
          var productId = params.get("product");
          var ticket = ticketId
            ? this.tickets.find(function (item) {
                return item.id === ticketId;
              })
            : null;
          if (ticket) {
            this.store.activeTicketId = ticket.id;
            this.store.activeProductId = ticket.productId;
            this.selectedTicketId = ticket.id;
            this.ensureBusinessCustomerText(ticket);
            if (pageType === "order") {
              this.drawerOpen = true;
              this.drawerMinimized = false;
            }
          } else if (productId) {
            this.store.activeProductId = productId;
          }
        },
        openDrawer: function (productId, ticketId) {
          this.store.activeProductId = productId;
          var ticket = ticketId
            ? this.tickets.find(function (item) {
                return item.id === ticketId;
              })
            : this.primaryTicket(productId);
          if (ticket) this.store.activeTicketId = ticket.id;
          if (ticket) this.ensureBusinessCustomerText(ticket);
          this.drawerOpen = true;
          this.drawerMinimized = false;
          this.activeTab = "handle";
          this.actionMode = "process";
          this.closeForm = { opinion: "", images: [] };
          this.showAllRecords = false;
          this.infoTab = "all";
          this.highlightedHistoryKey = "";
          this.save();
        },
        selectedTicket: function () {
          if (!this.selectedTicketId) return null;
          return (
            this.tickets.find(
              function (ticket) {
                return ticket.id === this.selectedTicketId;
              }.bind(this)
            ) || null
          );
        }
      },
      watch: {
        "newTicket.handler": function () {
          if (this.newTicket.templateId) this.applyIssueTemplate();
        },
        "newTicket.templateId": function (value) {
          if (value) this.applyIssueTemplate();
        }
      },
      mounted: function () {
        this.syncFromQuery(pageType);
        if (pageType === "templates" && this.issueTemplates.length) {
          this.editIssueTemplate(this.issueTemplates[0]);
        }
      },
      methods: {
        save: function () {
          saveStore(this.store);
        },
        stateMeta: function (stage) {
          return stateMeta[normalizeStage(stage)] || stateMeta.todo;
        },
        tagClass: tagClass,
        historyEntryTagClass: function (kind) {
          if (kind === "internal") return "blue";
          if (kind === "customer") return "green";
          return "gray";
        },
        summaryText: summaryText,
        productById: findProduct,
        productSpecKey: productSpecKey,
        orderNoOf: function (ticket) {
          return (ticket && ticket.orderNo) || ORDER_NO;
        },
        otherOrderNoOf: function (ticket, index) {
          var orderNo = this.orderNoOf(ticket);
          if (orderNo !== ORDER_NO) return orderNo;
          return "B2B-DD-KOR8-260517-" + String(145 + (Number(index) || 0)).padStart(3, "0");
        },
        customerNoOf: function (ticket) {
          return (ticket && ticket.customerNo) || CUSTOMER_NO;
        },
        sameSpecTickets: function (productId, excludeTicketId) {
          var currentProduct = findProduct(productId);
          var currentKey = productSpecKey(currentProduct);
          return this.tickets
            .filter(function (ticket) {
              if (excludeTicketId && ticket.id === excludeTicketId) return false;
              return productSpecKey(findProduct(ticket.productId)) === currentKey;
            })
            .sort(function (a, b) {
              return historyTimeValue(b.createdAt) - historyTimeValue(a.createdAt);
            });
        },
        sameSpecTicketsFiltered: function (productId, excludeTicketId, filter) {
          var self = this;
          var customerKeyword = String((filter && filter.customerNo) || "").trim();
          var orderKeyword = String((filter && filter.orderNo) || "").trim();
          var templateId = String((filter && filter.templateId) || "");
          return this.sameSpecTickets(productId, excludeTicketId).filter(function (ticket, index) {
            var visibleOrderNo = self.otherOrderNoOf(ticket, index);
            if (customerKeyword && self.customerNoOf(ticket).indexOf(customerKeyword) < 0) return false;
            if (orderKeyword && self.orderNoOf(ticket).indexOf(orderKeyword) < 0 && visibleOrderNo.indexOf(orderKeyword) < 0) return false;
            if (templateId === "__custom__" && ticket.templateId) return false;
            if (templateId && templateId !== "__custom__" && ticket.templateId !== templateId) return false;
            return true;
          });
        },
        openSameSpecTicket: function (ticket) {
          if (!ticket) return;
          var url =
            "代购订单详情.html?ticket=" +
            encodeURIComponent(ticket.id) +
            "&product=" +
            encodeURIComponent(ticket.productId || "");
          window.open(url, "_blank", "noopener");
        },
        languageLabel: languageLabel,
        setInfoTab: function (tab) {
          this.infoTab = tab;
          this.highlightedHistoryKey = "";
        },
        recordKey: function (record) {
          if (!record) return "";
          return ["record", record.time, record.actor, record.action, record.to, record.content].join("|");
        },
        messageKey: function (message) {
          if (!message) return "";
          return ["message", message.id || "", message.time, message.from, message.actor, message.choice, message.text].join("|");
        },
        showHistoryDetail: function (type, item) {
          if (!item) return;
          if (type === "internal") {
            this.infoTab = "internal";
            this.highlightedHistoryKey = this.recordKey(item);
          } else if (type === "customer") {
            this.infoTab = "customer";
            this.highlightedHistoryKey = this.messageKey(item);
          }
          this.$nextTick(function () {
            var node = document.querySelector(".history-focus-card");
            if (node) node.scrollIntoView({ block: "center", behavior: "smooth" });
          });
        },
        templateText: templateText,
        issueTemplateById: function (id) {
          return this.issueTemplates.find(function (template) {
            return template.id === id;
          }) || null;
        },
        issueTemplateName: function (ticket) {
          var template = this.issueTemplateById(ticket && ticket.templateId);
          return template && template.name ? template.name : "自定义内容";
        },
        templateCustomerText: function (ticket) {
          var template = this.issueTemplateById(ticket && ticket.templateId);
          return templateText(template, customerLanguageKey(ticket ? ticket.productId : "p1"));
        },
        ensureBusinessCustomerText: function (ticket) {
          if (!ticket || !this.isBusiness(ticket.currentHandler) || ticket.customerText) return;
          var text = this.templateCustomerText(ticket);
          if (text) ticket.customerText = text;
        },
        applyIssueTemplate: function () {
          if (!this.activeIssueTemplate) return;
          var text = templateText(this.activeIssueTemplate, this.newTicketLanguageKey);
          this.newTicket.issueText = text;
        },
        templateCompleteCount: function (template) {
          return templateLanguages.filter(function (language) {
            return Boolean(String((template.translations || {})[language.key] || "").trim());
          }).length;
        },
        editIssueTemplate: function (template) {
          this.templateEditingId = template ? template.id : "";
          this.issueTemplateForm = defaultTemplateForm(template || null);
          this.activeTemplateLang = "zh";
          this.toast = "";
        },
        newIssueTemplate: function () {
          this.templateEditingId = "";
          this.issueTemplateForm = defaultTemplateForm();
          this.activeTemplateLang = "zh";
          this.toast = "";
        },
        saveIssueTemplate: function () {
          var form = this.issueTemplateForm;
          if (!form.name.trim()) {
            this.toast = "请填写模板名称。";
            return;
          }
          if (!String(form.translations.zh || "").trim()) {
            this.toast = "请填写中文模板内容。";
            this.activeTemplateLang = "zh";
            return;
          }
          form.updatedAt = "刚刚";
          var index = this.issueTemplates.findIndex(
            function (template) {
              return template.id === this.templateEditingId;
            }.bind(this)
          );
          if (index >= 0) {
            this.store.issueTemplates.splice(index, 1, clone(form));
            this.toast = "模板已保存。";
          } else {
            if (!form.id) form.id = uid("tpl_");
            this.store.issueTemplates.unshift(clone(form));
            this.templateEditingId = form.id;
            this.toast = "模板已新增。";
          }
          this.save();
        },
        duplicateIssueTemplate: function (template) {
          var copy = clone(template);
          copy.id = uid("tpl_");
          copy.name = template.name + " 副本";
          copy.enabled = true;
          copy.updatedAt = "刚刚";
          this.store.issueTemplates.unshift(copy);
          this.editIssueTemplate(copy);
          this.toast = "已复制模板，可继续编辑。";
          this.save();
        },
        toggleIssueTemplate: function (template) {
          template.enabled = template.enabled === false;
          template.updatedAt = "刚刚";
          this.toast = template.enabled ? "模板已启用。" : "模板已停用。";
          this.save();
        },
        deleteIssueTemplate: function (template) {
          if (!template) return;
          if (!window.confirm("确认删除该模板？删除后创建工单中不再显示。")) return;
          var index = this.issueTemplates.findIndex(function (item) {
            return item.id === template.id;
          });
          if (index < 0) return;
          this.store.issueTemplates.splice(index, 1);
          if (this.templateEditingId === template.id) {
            if (this.issueTemplates.length) {
              this.editIssueTemplate(this.issueTemplates[0]);
            } else {
              this.newIssueTemplate();
            }
          }
          this.toast = "模板已删除。";
          this.save();
        },
        internalRecords: function (ticket) {
          return ensureRecords(ticket).slice().reverse();
        },
        allHistoryEntries: function (ticket) {
          if (!ticket) return [];
          var entries = [];
          entries.push({
            key: "issue|" + ticket.id,
            focusKey: "issue|" + ticket.id,
            kind: "issue",
            typeLabel: "工单内容",
            title: (ticket.proposer || "提出人") + " · 发起工单",
            time: ticket.createdAt || "",
            meta: "",
            templateLabel: this.issueTemplateName(ticket),
            content: ticket.issueText || "暂无问题内容。",
            physicalImages: this.physicalImages(ticket),
            linkImages: this.linkImages(ticket),
            images: []
          });

          ensureRecords(ticket).forEach(
            function (record) {
              entries.push({
                key: this.recordKey(record),
                focusKey: this.recordKey(record),
                kind: "internal",
                typeLabel: "内部处理",
                title: [record.actor, record.action].filter(Boolean).join(" · "),
                time: record.time || "",
                meta: record.to ? "转给：" + record.to : "",
                content: record.content || "",
                images: record.images || []
              });
            }.bind(this)
          );

          ensureConversations(ticket).forEach(
            function (message) {
              entries.push({
                key: this.messageKey(message),
                focusKey: this.messageKey(message),
                kind: "customer",
                typeLabel: "客户沟通",
                title: message.from === "客户" ? "客户回复" : "业务发送",
                time: message.time || "",
                meta: message.choice || (message.actor ? "发送人：" + message.actor : ""),
                content: message.text || "",
                images: message.images || []
              });
            }.bind(this)
          );

          return entries.sort(function (a, b) {
            return historyTimeValue(b.time) - historyTimeValue(a.time);
          });
        },
        visibleRecords: function (ticket) {
          var records = ensureRecords(ticket).slice().reverse();
          return this.showAllRecords ? records : records.slice(0, 3);
        },
        recordCount: function (ticket) {
          return ensureRecords(ticket).length;
        },
        customerImages: function (ticket) {
          return ensureCustomerImages(ticket);
        },
        customerPhysicalImages: function (ticket) {
          return ensureCustomerImageBuckets(ticket).physical;
        },
        customerLinkImages: function (ticket) {
          return ensureCustomerImageBuckets(ticket).link;
        },
        physicalImages: function (ticket) {
          if (!ticket) return [];
          if (Array.isArray(ticket.physicalImages) && ticket.physicalImages.length) return ticket.physicalImages;
          if (Array.isArray(ticket.linkImages) && ticket.linkImages.length) return [];
          return Array.isArray(ticket.images) ? ticket.images : [];
        },
        linkImages: function (ticket) {
          return ticket && Array.isArray(ticket.linkImages) ? ticket.linkImages : [];
        },
        selectedCustomerImages: function (ticket) {
          return ensureCustomerImages(ticket).filter(function (image) {
            return image.selected;
          });
        },
        physicalCustomerRecordImages: function (images) {
          return imagesByCustomerGroup(images, "physical");
        },
        linkCustomerRecordImages: function (images) {
          return imagesByCustomerGroup(images, "link");
        },
        conversations: function (ticket) {
          return ensureConversations(ticket).slice().reverse();
        },
        syncTargets: function (ticket) {
          var targets = [];
          function addTarget(person) {
            if (person && targets.indexOf(person) < 0) targets.push(person);
          }
          addTarget(ticket.proposer);
          ensureRecords(ticket)
            .slice()
            .reverse()
            .some(
              function (record) {
                if (record.actor && record.actor !== this.businessHandler && record.actor !== "客户") {
                  addTarget(record.actor);
                  return true;
                }
                return false;
              }.bind(this)
            );
          if (targets.length < 2 && ticket.currentHandler !== this.businessHandler) addTarget(ticket.currentHandler);
          return targets;
        },
        syncTargetText: function (ticket) {
          return this.syncTargets(ticket).join("、");
        },
        closedSyncTargets: function (ticket) {
          return ticket && ticket.syncTargets && ticket.syncTargets.length ? ticket.syncTargets : this.syncTargets(ticket);
        },
        flowLogs: function (ticket) {
          return (ticket.logs || []).slice().reverse();
        },
        latestCustomerMessage: function (ticket) {
          return latestCustomerMessage(ticket);
        },
        customerMessages: function (ticket) {
          return ensureConversations(ticket).filter(function (message) {
            return message.from === "客户";
          }).reverse();
        },
        hasCustomerReplies: function (ticket) {
          return this.customerMessages(ticket).length > 0;
        },
        latestInternalRecord: function (ticket) {
          var records = ensureRecords(ticket);
          return records.length ? records[records.length - 1] : null;
        },
        isBusiness: function (person) {
          return person === this.businessHandler;
        },
        samePerson: function (a, b) {
          if (!a || !b) return false;
          if (a === b) return true;
          var aName = String(a).trim().split(/\s+/).pop();
          var bName = String(b).trim().split(/\s+/).pop();
          return !!aName && aName === bName;
        },
        isWorkbenchRelatedTicket: function (ticket) {
          if (!ticket) return false;
          if (ticket.currentHandler === this.currentUser) return true;
          if (this.samePerson(ticket.proposer, DEMO_PROPOSER)) return true;
          return (ticket.syncTargets || []).indexOf(this.currentUser) >= 0;
        },
        canFinishTicket: function (ticket) {
          return !!ticket && (this.samePerson(ticket.proposer, this.currentUser) || this.samePerson(ticket.proposer, ticket.currentHandler));
        },
        productTickets: function (productId) {
          return this.tickets.filter(function (ticket) {
            return ticket.productId === productId;
          });
        },
        activeTickets: function (productId) {
          return this.productTickets(productId).filter(function (ticket) {
            return ticket.stage !== "closed";
          });
        },
        primaryTicket: function (productId) {
          var active = this.activeTickets(productId);
          if (active.length) return active[0];
          return this.productTickets(productId)[0] || null;
        },
        ticketStateLabel: function (ticket) {
          return this.stateMeta(ticket.stage).label;
        },
        currentOwnerText: function (ticket) {
          return ticket.currentHandler || "未指定";
        },
        nextActionLabel: function (ticket) {
          if (!ticket) return "查看";
          if (ticket.stage === "todo") return "去处理";
          if (ticket.stage === "waiting_customer") return "查看";
          if (ticket.stage === "customer_replied") return "同步客户信息";
          if (ticket.stage === "customer_confirmed") return this.canFinishTicket(ticket) ? "完结工单" : "去处理";
          return "查看";
        },
        currentNextText: function (ticket) {
          if (!ticket) return "";
          if (ticket.stage === "todo" && this.isBusiness(ticket.currentHandler)) {
            return "业务可发送客户确认，也可转交给其他处理人";
          }
          return this.stateMeta(ticket.stage).next;
        },
        flowClass: function (index, ticket) {
          if (!ticket) return "";
          var stage = normalizeStage(ticket.stage);
          var flow = this.stateMeta(stage).flow;
          if (stage === "closed") flow = flowSteps.length;
          if (index < flow) return "is-done";
          if (index === flow) return "is-current";
          return "";
        },
        syncFromQuery: function (pageType) {
          var params = new URLSearchParams(window.location.search);
          var ticketId = params.get("ticket");
          var productId = params.get("product");
          var ticket = ticketId
            ? this.tickets.find(function (item) {
                return item.id === ticketId;
              })
            : null;
          if (ticket) {
            this.store.activeTicketId = ticket.id;
            this.store.activeProductId = ticket.productId;
            this.selectedTicketId = ticket.id;
            this.ensureBusinessCustomerText(ticket);
            if (pageType === "order") {
              this.drawerOpen = true;
              this.drawerMinimized = false;
            }
          } else if (productId) {
            this.store.activeProductId = productId;
          }
        },
        openDrawer: function (productId, ticketId) {
          this.store.activeProductId = productId;
          var ticket = ticketId
            ? this.tickets.find(function (item) {
                return item.id === ticketId;
              })
            : this.primaryTicket(productId);
          if (ticket) this.store.activeTicketId = ticket.id;
          if (ticket) this.ensureBusinessCustomerText(ticket);
          this.drawerOpen = true;
          this.drawerMinimized = false;
          this.activeTab = "handle";
          this.actionMode = "process";
          this.closeForm = { opinion: "", images: [] };
          this.showAllRecords = false;
          this.infoTab = "all";
          this.highlightedHistoryKey = "";
          this.save();
        },
        selectTicket: function (ticket) {
          this.store.activeProductId = ticket.productId;
          this.store.activeTicketId = ticket.id;
          this.drawerOpen = true;
          this.drawerMinimized = false;
          this.activeTab = "handle";
          this.actionMode = "process";
          this.showAllRecords = false;
          this.infoTab = "all";
          this.highlightedHistoryKey = "";
          this.detailHistoryFilter = { customerNo: "", orderNo: "", templateId: "" };
          this.transferForm = { to: "", reason: "", images: [] };
          this.closeForm = { opinion: "", images: [] };
          this.replyForm = {
            choice: ticket.replyChoice || "可以接受",
            original: ticket.replyOriginal || ""
          };
          this.followupForm = { text: "" };
          this.ensureBusinessCustomerText(ticket);
          this.save();
        },
        openCreate: function (productId) {
          this.newTicket = defaultNewTicket(productId);
          this.createHistoryFilter = { customerNo: "", orderNo: "", templateId: "" };
          this.createOpen = true;
          this.createMinimized = false;
        },
        closeCreate: function () {
          this.createOpen = false;
          this.createMinimized = false;
        },
        closeDrawer: function () {
          this.drawerOpen = false;
          this.drawerMinimized = false;
        },
        minimizeDrawer: function () {
          this.drawerMinimized = true;
        },
        restoreDrawer: function () {
          this.drawerOpen = true;
          this.drawerMinimized = false;
        },
        minimizeCreate: function () {
          this.createMinimized = true;
        },
        restoreCreate: function () {
          this.createOpen = true;
          this.createMinimized = false;
        },
        submitNewTicket: function () {
          if (!this.newTicket.issueText.trim()) {
            this.toast = "请先填写问题内容。";
            return;
          }
          if (!this.newTicket.handler) {
            this.toast = "请选择处理人。";
            return;
          }
          var attachedImages = clone((this.newTicket.physicalImages || []).concat(this.newTicket.linkImages || []));
          var id = nextTicketId(this.store, this.newTicket.productId);
          var createdAt = currentTimeText();
          var ticket = makeTicket({
            id: id,
            productId: this.newTicket.productId,
            orderNo: this.orderNo,
            customerNo: this.customerNo,
            stage: "todo",
            proposer: DEMO_PROPOSER,
            currentHandler: this.newTicket.handler,
            createdAt: createdAt,
            templateId: this.newTicket.templateId,
            issueText: this.newTicket.issueText,
            customerText: "",
            images: attachedImages.length ? attachedImages : [imageStub("待上传图片", "blank")],
            physicalImages: this.newTicket.physicalImages.length ? clone(this.newTicket.physicalImages) : [],
            linkImages: this.newTicket.linkImages.length ? clone(this.newTicket.linkImages) : [],
            customerPhysicalImages: this.newTicket.physicalImages.length
              ? selectedImages(this.newTicket.physicalImages).map(function (image) {
                  return markCustomerImage(image, "physical");
                })
              : [],
            customerLinkImages: this.newTicket.linkImages.length
              ? selectedImages(this.newTicket.linkImages).map(function (image) {
                  return markCustomerImage(image, "link");
                })
              : [],
            customerImages: attachedImages.length
              ? selectedImages(attachedImages)
              : [Object.assign(imageStub("待上传图片", "blank"), { selected: true })],
            logs: [
              {
                time: createdAt,
                actor: DEMO_PROPOSER,
                action: "发起工单",
                detail: "提交商品问题，并指定处理人：" + this.newTicket.handler
              }
            ]
          });
          this.store.tickets.unshift(ticket);
          this.store.activeProductId = ticket.productId;
          this.store.activeTicketId = ticket.id;
          this.createOpen = false;
          this.createMinimized = false;
          this.drawerOpen = true;
          this.drawerMinimized = false;
          this.toast = "工单已创建，已进入处理人待办。";
          this.save();
        },
        setActionMode: function (mode) {
          if (mode === "transfer") {
            var ticket = this.currentTicket;
            var lastRecord = ticket ? this.latestInternalRecord(ticket) : null;
            if (ticket && !this.transferForm.reason) {
              this.transferForm.reason = ticket.handlerOpinion || (lastRecord && lastRecord.content) || ticket.issueText || "";
            }
          }
          if (mode === "close") {
            var closeTicket = this.currentTicket;
            if (closeTicket && !this.canFinishTicket(closeTicket)) {
              this.actionMode = "process";
              this.toast = "只有工单发起人可以完结工单。";
              return;
            }
            if (closeTicket && !this.closeForm.opinion) {
              this.closeForm.opinion = closeTicket.handlerOpinion || closeTicket.replyTranslation || closeTicket.closeResult || "";
            }
            if (closeTicket && (!this.closeForm.images || !this.closeForm.images.length)) {
              this.closeForm.images = clone(closeTicket.handlerImages || []);
            }
          }
          this.actionMode = mode;
          this.toast = "";
        },
        saveDraft: function () {
          var ticket = this.currentTicket;
          if (!ticket) return;
          addLog(ticket, ticket.currentHandler, "保存草稿", "已保存当前填写内容。");
          this.toast = "已保存。";
          this.save();
        },
        submitHandlerOpinion: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage !== "todo") return;
          var opinion = String(ticket.handlerOpinion || "").trim();
          var images = clone(ticket.handlerImages || []);
          if (!opinion && !images.length) {
            this.toast = "请填写本次处理意见，或上传图片附件。";
            return;
          }
          var previous = ticket.currentHandler;
          var nextHandler = this.isBusiness(previous) ? previous : this.businessHandler;
          addRecord(ticket, previous, "提交处理意见", opinion || "已上传图片附件。", nextHandler, images);
          addLog(
            ticket,
            previous,
            "提交处理意见",
            this.isBusiness(previous) ? "已提交业务处理意见。" : "已提交处理意见，回到订单业务汇总。"
          );
          if (!this.isBusiness(previous)) {
            ticket.currentHandler = this.businessHandler;
            this.ensureBusinessCustomerText(ticket);
            ticket.handlerOpinion = "";
            ticket.handlerImages = [];
            this.toast = "处理意见已提交，工单已回到订单业务汇总。";
          } else {
            this.toast = "处理意见已提交，可继续发送客户确认或完结工单。";
          }
          this.actionMode = "process";
          this.infoTab = "internal";
          this.highlightedHistoryKey = "";
          this.save();
        },
        transferTicket: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage === "closed") return;
          if (ticket.stage === "waiting_customer") {
            this.toast = "待客户确认阶段不可转交。";
            this.actionMode = "process";
            return;
          }
          if (!this.transferForm.to) {
            this.toast = "请选择新的处理人。";
            return;
          }
          if (!this.transferForm.reason.trim()) {
            this.toast = "请填写转交原因。";
            return;
          }
          var previous = ticket.currentHandler;
          var to = this.transferForm.to;
          var content = this.transferForm.reason;
          var transferImages = this.transferForm.images.length ? this.transferForm.images : ticket.handlerImages || [];
          addRecord(ticket, previous, this.isBusiness(to) ? "转交业务" : "转交工单", content, to, transferImages);
          ticket.currentHandler = this.transferForm.to;
          ticket.stage = "todo";
          this.ensureBusinessCustomerText(ticket);
          addLog(
            ticket,
            previous,
            "转交工单",
            "转交给 " + ticket.currentHandler + (this.transferForm.reason ? "，原因：" + this.transferForm.reason : "")
          );
          ticket.handlerOpinion = "";
          ticket.handlerImages = [];
          this.transferForm = { to: "", reason: "", images: [] };
          this.actionMode = "process";
          this.toast = "已转交给新的处理人。";
          this.save();
        },
        sendCustomer: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage !== "todo" || !this.isBusiness(ticket.currentHandler)) return;
          if (!ticket.customerText || !ticket.customerText.trim()) {
            this.toast = "请填写发送给客户的内容。";
            return;
          }
          var sendImages = this.selectedCustomerImages(ticket);
          ticket.stage = "waiting_customer";
          ticket.currentHandler = this.businessHandler;
          addConversation(ticket, "业务", this.businessHandler, ticket.customerText, sendImages, "");
          addRecord(
            ticket,
            this.businessHandler,
            "发送客户确认",
            "已发送客户语言内容" + (sendImages.length ? "和 " + sendImages.length + " 张图片。" : "。"),
            "客户"
          );
          addLog(ticket, this.businessHandler, "发送客户确认", "已发送客户语言内容，等待客户回复。");
          this.toast = "已发送客户确认，工单进入待客户确认。";
          this.save();
        },
        recordCustomerReply: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage !== "waiting_customer") return;
          if (!this.replyForm.original.trim()) {
            this.toast = "请填写模拟客户原文。";
            return;
          }
          ticket.replyChoice = this.replyForm.choice;
          ticket.replyOriginal = this.replyForm.original;
          ticket.stage = "customer_replied";
          ticket.currentHandler = this.businessHandler;
          addConversation(ticket, "客户", "客户", ticket.replyOriginal, [], ticket.replyChoice);
          addRecord(ticket, "客户", "客户回复", ticket.replyChoice + "；" + ticket.replyOriginal, this.businessHandler);
          addLog(ticket, "客户", "客户回复", ticket.replyChoice + "；" + ticket.replyOriginal);
          this.actionMode = "process";
          this.toast = "已保存模拟客户回复，等待业务翻译并同步客户信息。";
          this.save();
        },
        sendFollowupToCustomer: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage !== "customer_replied") return;
          if (!this.followupForm.text.trim()) {
            this.toast = "请填写继续回复客户的内容。";
            return;
          }
          var followupImages = this.selectedCustomerImages(ticket);
          ticket.customerFollowText = this.followupForm.text;
          ticket.customerText = this.followupForm.text;
          ticket.stage = "waiting_customer";
          ticket.currentHandler = this.businessHandler;
          addConversation(ticket, "业务", this.businessHandler, ticket.customerFollowText, followupImages, "");
          addRecord(
            ticket,
            this.businessHandler,
            "继续回复客户",
            "已继续发送客户内容" + (followupImages.length ? "和 " + followupImages.length + " 张图片。" : "。"),
            "客户"
          );
          addLog(ticket, this.businessHandler, "继续回复客户", "客户仍需沟通，已再次发送客户确认内容。");
          this.followupForm = { text: "" };
          this.actionMode = "process";
          this.toast = "已继续回复客户，工单回到待客户确认。";
          this.save();
        },
        syncCustomerInfo: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage !== "customer_replied") return;
          if (!ticket.replyTranslation || !ticket.replyTranslation.trim()) {
            this.toast = "请先填写客户内容翻译。";
            return;
          }
          ticket.syncTargets = this.syncTargets(ticket);
          ticket.closeResult =
            "客户选择：" + (ticket.replyChoice || "未选择") + "；客户内容翻译：" + ticket.replyTranslation;
          ticket.stage = "customer_confirmed";
          ticket.currentHandler = this.businessHandler;
          addRecord(ticket, this.businessHandler, "同步客户信息", ticket.closeResult, ticket.syncTargets.join(" / "));
          addLog(ticket, this.businessHandler, "同步客户信息", "已同步给：" + ticket.syncTargets.join("、"));
          this.actionMode = "process";
          this.toast = "客户信息已同步到提出人和处理人的待办。";
          this.save();
        },
        closeTicket: function () {
          var ticket = this.currentTicket;
          if (!ticket || ticket.stage === "closed") return;
          if (!this.canFinishTicket(ticket)) {
            this.toast = "只有工单发起人可以完结工单。";
            return;
          }
          if (!this.closeForm.opinion.trim()) {
            this.toast = "请填写本次处理意见。";
            return;
          }
          var closeOpinion = this.closeForm.opinion;
          var closeImages = clone(this.closeForm.images || []);
          var closeTargets = this.syncTargets(ticket);
          ticket.syncTargets = closeTargets;
          ticket.closeResult = closeOpinion;
          ticket.closeImages = closeImages;
          ticket.handlerOpinion = closeOpinion;
          ticket.handlerImages = closeImages;
          ticket.stage = "closed";
          addRecord(ticket, ticket.currentHandler, "完结工单并同步", closeOpinion, closeTargets.join(" / "), closeImages);
          addLog(ticket, ticket.currentHandler, "完结工单", "已完结并同步给：" + closeTargets.join("、"));
          this.closeForm = { opinion: "", images: [] };
          this.actionMode = "process";
          this.toast = "工单已完结，并同步给默认人员。";
          this.save();
        },
        openTicketFromWorkbench: function (ticket) {
          window.location.href = "代购订单详情.html?ticket=" + encodeURIComponent(ticket.id);
        },
        setWorkbenchMode: function (mode) {
          this.workbenchMode = mode === "history" ? "history" : "todo";
          this.activeFilter = this.workbenchMode === "history" ? "todo" : "mine";
        },
        resetFilters: function () {
          this.searchOrder = "";
          this.customerQuery = "";
          this.filterStage = "all";
          this.filterHandler = "all";
          this.filterDateStart = "";
          this.filterDateEnd = "";
        },
        handleFileImages: function (event, target) {
          var files = Array.prototype.slice.call(event.target.files || []);
          this.readImageFiles(files, target || this.newTicket.physicalImages);
          event.target.value = "";
        },
        handlePasteImages: function (event, target) {
          var items = Array.prototype.slice.call((event.clipboardData && event.clipboardData.items) || []);
          var files = items
            .filter(function (item) {
              return item.type && item.type.indexOf("image/") === 0;
            })
            .map(function (item) {
              return item.getAsFile();
            })
            .filter(Boolean);
          if (!files.length) {
            this.toast = "剪贴板中没有图片。";
            return;
          }
          this.readImageFiles(files, target || this.newTicket.physicalImages);
        },
        handleDragOver: function () {},
        handleDropImages: function (event, target) {
          var files = Array.prototype.slice.call((event.dataTransfer && event.dataTransfer.files) || []).filter(function (file) {
            return file.type && file.type.indexOf("image/") === 0;
          });
          if (!files.length) {
            this.toast = "请拖入图片文件。";
            return;
          }
          this.readImageFiles(files, target || this.newTicket.physicalImages);
        },
        readImageFiles: function (files, target) {
          var self = this;
          files.forEach(function (file) {
            var reader = new FileReader();
            reader.onload = function (event) {
              target.push({
                id: uid("img_"),
                name: file.name || "粘贴图片",
                theme: "uploaded",
                url: event.target.result,
                selected: true
              });
              self.save();
            };
            reader.readAsDataURL(file);
          });
        },
        removeImage: function (target, imageId) {
          var index = target.findIndex(function (image) {
            return image.id === imageId;
          });
          if (index >= 0) target.splice(index, 1);
          this.save();
        },
        openImagePreview: function (image) {
          if (!image) return;
          this.previewImage = image;
        },
        closeImagePreview: function () {
          this.previewImage = null;
        }
      }
    };
  }

  function mountApp(id, type) {
    if (!document.getElementById(id)) return false;
    createApp(buildApp(type)).mount("#" + id);
    return true;
  }

  try {
    var mounted =
      mountApp("orderApp", "order") ||
      mountApp("workbenchApp", "workbench") ||
      mountApp("issueTemplateApp", "templates");
    if (mounted) markBootReady();
  } catch (error) {
    console.error(error);
    setBootMessage("页面加载失败：" + (error && error.message ? error.message : error), true);
    revealCloaked();
  }
})();
