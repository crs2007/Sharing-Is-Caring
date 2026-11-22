/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const N = globalThis, q = N.ShadowRoot && (N.ShadyCSS === void 0 || N.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, K = Symbol(), J = /* @__PURE__ */ new WeakMap();
let le = class {
  constructor(e, t, s) {
    if (this._$cssResult$ = !0, s !== K) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (q && e === void 0) {
      const s = t !== void 0 && t.length === 1;
      s && (e = J.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), s && J.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const ue = (i) => new le(typeof i == "string" ? i : i + "", void 0, K), be = (i, ...e) => {
  const t = i.length === 1 ? i[0] : e.reduce((s, r, o) => s + ((a) => {
    if (a._$cssResult$ === !0) return a.cssText;
    if (typeof a == "number") return a;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + a + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + i[o + 1], i[0]);
  return new le(t, i, K);
}, _e = (i, e) => {
  if (q) i.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const s = document.createElement("style"), r = N.litNonce;
    r !== void 0 && s.setAttribute("nonce", r), s.textContent = t.cssText, i.appendChild(s);
  }
}, Y = q ? (i) => i : (i) => i instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const s of e.cssRules) t += s.cssText;
  return ue(t);
})(i) : i;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ge, defineProperty: fe, getOwnPropertyDescriptor: ve, getOwnPropertyNames: me, getOwnPropertySymbols: ye, getPrototypeOf: $e } = Object, y = globalThis, Q = y.trustedTypes, xe = Q ? Q.emptyScript : "", j = y.reactiveElementPolyfillSupport, C = (i, e) => i, M = { toAttribute(i, e) {
  switch (e) {
    case Boolean:
      i = i ? xe : null;
      break;
    case Object:
    case Array:
      i = i == null ? i : JSON.stringify(i);
  }
  return i;
}, fromAttribute(i, e) {
  let t = i;
  switch (e) {
    case Boolean:
      t = i !== null;
      break;
    case Number:
      t = i === null ? null : Number(i);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(i);
      } catch {
        t = null;
      }
  }
  return t;
} }, V = (i, e) => !ge(i, e), X = { attribute: !0, type: String, converter: M, reflect: !1, useDefault: !1, hasChanged: V };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), y.litPropertyMetadata ?? (y.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let S = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = X) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const s = Symbol(), r = this.getPropertyDescriptor(e, s, t);
      r !== void 0 && fe(this.prototype, e, r);
    }
  }
  static getPropertyDescriptor(e, t, s) {
    const { get: r, set: o } = ve(this.prototype, e) ?? { get() {
      return this[t];
    }, set(a) {
      this[t] = a;
    } };
    return { get: r, set(a) {
      const l = r == null ? void 0 : r.call(this);
      o == null || o.call(this, a), this.requestUpdate(e, l, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? X;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const e = $e(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const t = this.properties, s = [...me(t), ...ye(t)];
      for (const r of s) this.createProperty(r, t[r]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [s, r] of t) this.elementProperties.set(s, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, s] of this.elementProperties) {
      const r = this._$Eu(t, s);
      r !== void 0 && this._$Eh.set(r, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const s = new Set(e.flat(1 / 0).reverse());
      for (const r of s) t.unshift(Y(r));
    } else e !== void 0 && t.push(Y(e));
    return t;
  }
  static _$Eu(e, t) {
    const s = t.attribute;
    return s === !1 ? void 0 : typeof s == "string" ? s : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var e;
    this._$ES = new Promise((t) => this.enableUpdating = t), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (e = this.constructor.l) == null || e.forEach((t) => t(this));
  }
  addController(e) {
    var t;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(e), this.renderRoot !== void 0 && this.isConnected && ((t = e.hostConnected) == null || t.call(e));
  }
  removeController(e) {
    var t;
    (t = this._$EO) == null || t.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const s of t.keys()) this.hasOwnProperty(s) && (e.set(s, this[s]), delete this[s]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return _e(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((t) => {
      var s;
      return (s = t.hostConnected) == null ? void 0 : s.call(t);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((t) => {
      var s;
      return (s = t.hostDisconnected) == null ? void 0 : s.call(t);
    });
  }
  attributeChangedCallback(e, t, s) {
    this._$AK(e, s);
  }
  _$ET(e, t) {
    var o;
    const s = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, s);
    if (r !== void 0 && s.reflect === !0) {
      const a = (((o = s.converter) == null ? void 0 : o.toAttribute) !== void 0 ? s.converter : M).toAttribute(t, s.type);
      this._$Em = e, a == null ? this.removeAttribute(r) : this.setAttribute(r, a), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var o, a;
    const s = this.constructor, r = s._$Eh.get(e);
    if (r !== void 0 && this._$Em !== r) {
      const l = s.getPropertyOptions(r), n = typeof l.converter == "function" ? { fromAttribute: l.converter } : ((o = l.converter) == null ? void 0 : o.fromAttribute) !== void 0 ? l.converter : M;
      this._$Em = r;
      const b = n.fromAttribute(t, l.type);
      this[r] = b ?? ((a = this._$Ej) == null ? void 0 : a.get(r)) ?? b, this._$Em = null;
    }
  }
  requestUpdate(e, t, s, r = !1, o) {
    var a;
    if (e !== void 0) {
      const l = this.constructor;
      if (r === !1 && (o = this[e]), s ?? (s = l.getPropertyOptions(e)), !((s.hasChanged ?? V)(o, t) || s.useDefault && s.reflect && o === ((a = this._$Ej) == null ? void 0 : a.get(e)) && !this.hasAttribute(l._$Eu(e, s)))) return;
      this.C(e, t, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: s, reflect: r, wrapped: o }, a) {
    s && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), o !== !0 || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || s || (t = void 0), this._$AL.set(e, t)), r === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var s;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [o, a] of this._$Ep) this[o] = a;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [o, a] of r) {
        const { wrapped: l } = a, n = this[o];
        l !== !0 || this._$AL.has(o) || n === void 0 || this.C(o, void 0, a, n);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (s = this._$EO) == null || s.forEach((r) => {
        var o;
        return (o = r.hostUpdate) == null ? void 0 : o.call(r);
      }), this.update(t)) : this._$EM();
    } catch (r) {
      throw e = !1, this._$EM(), r;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var t;
    (t = this._$EO) == null || t.forEach((s) => {
      var r;
      return (r = s.hostUpdated) == null ? void 0 : r.call(s);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t) => this._$ET(t, this[t]))), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
S.elementStyles = [], S.shadowRootOptions = { mode: "open" }, S[C("elementProperties")] = /* @__PURE__ */ new Map(), S[C("finalized")] = /* @__PURE__ */ new Map(), j == null || j({ ReactiveElement: S }), (y.reactiveElementVersions ?? (y.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const R = globalThis, ee = (i) => i, L = R.trustedTypes, te = L ? L.createPolicy("lit-html", { createHTML: (i) => i }) : void 0, de = "$lit$", m = `lit$${Math.random().toFixed(9).slice(2)}$`, ce = "?" + m, we = `<${ce}>`, A = document, U = () => A.createComment(""), z = (i) => i === null || typeof i != "object" && typeof i != "function", G = Array.isArray, Ae = (i) => G(i) || typeof (i == null ? void 0 : i[Symbol.iterator]) == "function", D = `[ 	
\f\r]`, P = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ie = /-->/g, se = />/g, $ = RegExp(`>|${D}(?:([^\\s"'>=/]+)(${D}*=${D}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), re = /'/g, oe = /"/g, pe = /^(?:script|style|textarea|title)$/i, Se = (i) => (e, ...t) => ({ _$litType$: i, strings: e, values: t }), c = Se(1), k = Symbol.for("lit-noChange"), d = Symbol.for("lit-nothing"), ae = /* @__PURE__ */ new WeakMap(), x = A.createTreeWalker(A, 129);
function he(i, e) {
  if (!G(i) || !i.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return te !== void 0 ? te.createHTML(e) : e;
}
const ke = (i, e) => {
  const t = i.length - 1, s = [];
  let r, o = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", a = P;
  for (let l = 0; l < t; l++) {
    const n = i[l];
    let b, g, h = -1, f = 0;
    for (; f < n.length && (a.lastIndex = f, g = a.exec(n), g !== null); ) f = a.lastIndex, a === P ? g[1] === "!--" ? a = ie : g[1] !== void 0 ? a = se : g[2] !== void 0 ? (pe.test(g[2]) && (r = RegExp("</" + g[2], "g")), a = $) : g[3] !== void 0 && (a = $) : a === $ ? g[0] === ">" ? (a = r ?? P, h = -1) : g[1] === void 0 ? h = -2 : (h = a.lastIndex - g[2].length, b = g[1], a = g[3] === void 0 ? $ : g[3] === '"' ? oe : re) : a === oe || a === re ? a = $ : a === ie || a === se ? a = P : (a = $, r = void 0);
    const v = a === $ && i[l + 1].startsWith("/>") ? " " : "";
    o += a === P ? n + we : h >= 0 ? (s.push(b), n.slice(0, h) + de + n.slice(h) + m + v) : n + m + (h === -2 ? l : v);
  }
  return [he(i, o + (i[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), s];
};
class T {
  constructor({ strings: e, _$litType$: t }, s) {
    let r;
    this.parts = [];
    let o = 0, a = 0;
    const l = e.length - 1, n = this.parts, [b, g] = ke(e, t);
    if (this.el = T.createElement(b, s), x.currentNode = this.el.content, t === 2 || t === 3) {
      const h = this.el.content.firstChild;
      h.replaceWith(...h.childNodes);
    }
    for (; (r = x.nextNode()) !== null && n.length < l; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const h of r.getAttributeNames()) if (h.endsWith(de)) {
          const f = g[a++], v = r.getAttribute(h).split(m), H = /([.?@])?(.*)/.exec(f);
          n.push({ type: 1, index: o, name: H[2], strings: v, ctor: H[1] === "." ? Pe : H[1] === "?" ? Ce : H[1] === "@" ? Re : B }), r.removeAttribute(h);
        } else h.startsWith(m) && (n.push({ type: 6, index: o }), r.removeAttribute(h));
        if (pe.test(r.tagName)) {
          const h = r.textContent.split(m), f = h.length - 1;
          if (f > 0) {
            r.textContent = L ? L.emptyScript : "";
            for (let v = 0; v < f; v++) r.append(h[v], U()), x.nextNode(), n.push({ type: 2, index: ++o });
            r.append(h[f], U());
          }
        }
      } else if (r.nodeType === 8) if (r.data === ce) n.push({ type: 2, index: o });
      else {
        let h = -1;
        for (; (h = r.data.indexOf(m, h + 1)) !== -1; ) n.push({ type: 7, index: o }), h += m.length - 1;
      }
      o++;
    }
  }
  static createElement(e, t) {
    const s = A.createElement("template");
    return s.innerHTML = e, s;
  }
}
function E(i, e, t = i, s) {
  var a, l;
  if (e === k) return e;
  let r = s !== void 0 ? (a = t._$Co) == null ? void 0 : a[s] : t._$Cl;
  const o = z(e) ? void 0 : e._$litDirective$;
  return (r == null ? void 0 : r.constructor) !== o && ((l = r == null ? void 0 : r._$AO) == null || l.call(r, !1), o === void 0 ? r = void 0 : (r = new o(i), r._$AT(i, t, s)), s !== void 0 ? (t._$Co ?? (t._$Co = []))[s] = r : t._$Cl = r), r !== void 0 && (e = E(i, r._$AS(i, e.values), r, s)), e;
}
class Ee {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: s } = this._$AD, r = ((e == null ? void 0 : e.creationScope) ?? A).importNode(t, !0);
    x.currentNode = r;
    let o = x.nextNode(), a = 0, l = 0, n = s[0];
    for (; n !== void 0; ) {
      if (a === n.index) {
        let b;
        n.type === 2 ? b = new I(o, o.nextSibling, this, e) : n.type === 1 ? b = new n.ctor(o, n.name, n.strings, this, e) : n.type === 6 && (b = new Oe(o, this, e)), this._$AV.push(b), n = s[++l];
      }
      a !== (n == null ? void 0 : n.index) && (o = x.nextNode(), a++);
    }
    return x.currentNode = A, r;
  }
  p(e) {
    let t = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(e, s, t), t += s.strings.length - 2) : s._$AI(e[t])), t++;
  }
}
class I {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, s, r) {
    this.type = 2, this._$AH = d, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = s, this.options = r, this._$Cv = (r == null ? void 0 : r.isConnected) ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && (e == null ? void 0 : e.nodeType) === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = E(this, e, t), z(e) ? e === d || e == null || e === "" ? (this._$AH !== d && this._$AR(), this._$AH = d) : e !== this._$AH && e !== k && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Ae(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== d && z(this._$AH) ? this._$AA.nextSibling.data = e : this.T(A.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var o;
    const { values: t, _$litType$: s } = e, r = typeof s == "number" ? this._$AC(e) : (s.el === void 0 && (s.el = T.createElement(he(s.h, s.h[0]), this.options)), s);
    if (((o = this._$AH) == null ? void 0 : o._$AD) === r) this._$AH.p(t);
    else {
      const a = new Ee(r, this), l = a.u(this.options);
      a.p(t), this.T(l), this._$AH = a;
    }
  }
  _$AC(e) {
    let t = ae.get(e.strings);
    return t === void 0 && ae.set(e.strings, t = new T(e)), t;
  }
  k(e) {
    G(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let s, r = 0;
    for (const o of e) r === t.length ? t.push(s = new I(this.O(U()), this.O(U()), this, this.options)) : s = t[r], s._$AI(o), r++;
    r < t.length && (this._$AR(s && s._$AB.nextSibling, r), t.length = r);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, t); e !== this._$AB; ) {
      const r = ee(e).nextSibling;
      ee(e).remove(), e = r;
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 && (this._$Cv = e, (t = this._$AP) == null || t.call(this, e));
  }
}
class B {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, s, r, o) {
    this.type = 1, this._$AH = d, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = o, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = d;
  }
  _$AI(e, t = this, s, r) {
    const o = this.strings;
    let a = !1;
    if (o === void 0) e = E(this, e, t, 0), a = !z(e) || e !== this._$AH && e !== k, a && (this._$AH = e);
    else {
      const l = e;
      let n, b;
      for (e = o[0], n = 0; n < o.length - 1; n++) b = E(this, l[s + n], t, n), b === k && (b = this._$AH[n]), a || (a = !z(b) || b !== this._$AH[n]), b === d ? e = d : e !== d && (e += (b ?? "") + o[n + 1]), this._$AH[n] = b;
    }
    a && !r && this.j(e);
  }
  j(e) {
    e === d ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Pe extends B {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === d ? void 0 : e;
  }
}
class Ce extends B {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== d);
  }
}
class Re extends B {
  constructor(e, t, s, r, o) {
    super(e, t, s, r, o), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = E(this, e, t, 0) ?? d) === k) return;
    const s = this._$AH, r = e === d && s !== d || e.capture !== s.capture || e.once !== s.once || e.passive !== s.passive, o = e !== d && (s === d || r);
    r && this.element.removeEventListener(this.name, this, s), o && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function" ? this._$AH.call(((t = this.options) == null ? void 0 : t.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Oe {
  constructor(e, t, s) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    E(this, e);
  }
}
const F = R.litHtmlPolyfillSupport;
F == null || F(T, I), (R.litHtmlVersions ?? (R.litHtmlVersions = [])).push("3.3.3");
const Ue = (i, e, t) => {
  const s = (t == null ? void 0 : t.renderBefore) ?? e;
  let r = s._$litPart$;
  if (r === void 0) {
    const o = (t == null ? void 0 : t.renderBefore) ?? null;
    s._$litPart$ = r = new I(e.insertBefore(U(), o), o, void 0, t ?? {});
  }
  return r._$AI(i), r;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w = globalThis;
class O extends S {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var t;
    const e = super.createRenderRoot();
    return (t = this.renderOptions).renderBefore ?? (t.renderBefore = e.firstChild), e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ue(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var e;
    super.connectedCallback(), (e = this._$Do) == null || e.setConnected(!0);
  }
  disconnectedCallback() {
    var e;
    super.disconnectedCallback(), (e = this._$Do) == null || e.setConnected(!1);
  }
  render() {
    return k;
  }
}
var ne;
O._$litElement$ = !0, O.finalized = !0, (ne = w.litElementHydrateSupport) == null || ne.call(w, { LitElement: O });
const W = w.litElementPolyfillSupport;
W == null || W({ LitElement: O });
(w.litElementVersions ?? (w.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ze = (i) => (e, t) => {
  t !== void 0 ? t.addInitializer(() => {
    customElements.define(i, e);
  }) : customElements.define(i, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Te = { attribute: !0, type: String, converter: M, reflect: !1, hasChanged: V }, Ie = (i = Te, e, t) => {
  const { kind: s, metadata: r } = t;
  let o = globalThis.litPropertyMetadata.get(r);
  if (o === void 0 && globalThis.litPropertyMetadata.set(r, o = /* @__PURE__ */ new Map()), s === "setter" && ((i = Object.create(i)).wrapped = !0), o.set(t.name, i), s === "accessor") {
    const { name: a } = t;
    return { set(l) {
      const n = e.get.call(this);
      e.set.call(this, l), this.requestUpdate(a, n, i, !0, l);
    }, init(l) {
      return l !== void 0 && this.C(a, void 0, i, l), l;
    } };
  }
  if (s === "setter") {
    const { name: a } = t;
    return function(l) {
      const n = this[a];
      e.call(this, l), this.requestUpdate(a, n, i, !0, l);
    };
  }
  throw Error("Unsupported decorator location: " + s);
};
function Z(i) {
  return (e, t) => typeof t == "object" ? Ie(i, e, t) : ((s, r, o) => {
    const a = r.hasOwnProperty(o);
    return r.constructor.createProperty(o, s), a ? Object.getOwnPropertyDescriptor(r, o) : void 0;
  })(i, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function _(i) {
  return Z({ ...i, state: !0, attribute: !1 });
}
var He = Object.defineProperty, Ne = Object.getOwnPropertyDescriptor, u = (i, e, t, s) => {
  for (var r = s > 1 ? void 0 : s ? Ne(e, t) : e, o = i.length - 1, a; o >= 0; o--)
    (a = i[o]) && (r = (s ? a(e, t, r) : a(r)) || r);
  return s && r && He(e, t, r), r;
};
let p = class extends O {
  constructor() {
    super(...arguments), this.narrow = !1, this._step = 1, this._loading = !1, this._error = "", this._copiedKey = "", this._status = null, this._items = [], this._search = "", this._domainFilter = "all", this._selectedEntityId = "", this._titleOverride = "", this._descriptionOverride = "", this._includeCompanionScripts = !0, this._generateBlueprint = !0, this._preview = null, this._activeFileTab = "", this._customRedactionsInput = "", this._textOverrides = {}, this._selectedProvider = "github_gist", this._visibility = "secret", this._confirmReviewItems = !1, this._shareResult = null;
  }
  firstUpdated() {
    this._loadInitialData();
  }
  async _loadInitialData() {
    if (this.hass) {
      this._loading = !0, this._error = "";
      try {
        const [i, e] = await Promise.all([
          this.hass.callWS({ type: "sharing_is_caring/get_status" }),
          this.hass.callWS({
            type: "sharing_is_caring/list_shareables"
          })
        ]);
        this._status = i, this._items = e.items ?? [], this._visibility = i.default_visibility || "secret", this._selectedProvider = i.github_configured ? "github_gist" : "local";
      } catch (i) {
        this._error = this._formatError(i);
      } finally {
        this._loading = !1;
      }
    }
  }
  _formatError(i) {
    return i && typeof i == "object" && "message" in i ? String(i.message) : String(i ?? "Unexpected error");
  }
  _parseCustomRedactions() {
    return this._customRedactionsInput.split(",").map((i) => i.trim()).filter((i) => i.length >= 2);
  }
  async _runPreview() {
    if (this._selectedEntityId) {
      this._loading = !0, this._error = "", this._confirmReviewItems = !1, this._shareResult = null;
      try {
        const i = {
          type: "sharing_is_caring/preview",
          entity_id: this._selectedEntityId,
          include_companion_scripts: this._includeCompanionScripts,
          generate_blueprint: this._generateBlueprint,
          custom_redactions: this._parseCustomRedactions(),
          text_overrides: this._textOverrides
        };
        this._titleOverride.trim() && (i.title = this._titleOverride.trim()), this._descriptionOverride.trim() && (i.description = this._descriptionOverride.trim());
        const e = await this.hass.callWS(i);
        this._preview = e;
        const t = Object.keys(e.files);
        t.includes(this._activeFileTab) || (this._activeFileTab = e.package_filename || t[0] || ""), this._step = 2;
      } catch (i) {
        this._error = this._formatError(i);
      } finally {
        this._loading = !1;
      }
    }
  }
  async _publishBundle() {
    if (this._preview) {
      this._loading = !0, this._error = "";
      try {
        const i = await this.hass.callWS({
          type: "sharing_is_caring/publish",
          preview_hash: this._preview.preview_hash,
          provider: this._selectedProvider,
          visibility: this._visibility,
          confirm_review_items: this._confirmReviewItems
        });
        this._shareResult = i;
      } catch (i) {
        this._error = this._formatError(i);
      } finally {
        this._loading = !1;
      }
    }
  }
  async _copyText(i, e) {
    try {
      await navigator.clipboard.writeText(e), this._copiedKey = i, window.setTimeout(() => {
        this._copiedKey === i && (this._copiedKey = "");
      }, 2e3);
    } catch {
      this._error = "Clipboard copy was blocked by your browser.";
    }
  }
  _downloadFile(i, e) {
    const t = new Blob([e], { type: "text/plain;charset=utf-8" }), s = URL.createObjectURL(t), r = document.createElement("a");
    r.href = s, r.download = i, document.body.appendChild(r), r.click(), document.body.removeChild(r), URL.revokeObjectURL(s);
  }
  _downloadAllFiles(i) {
    for (const [e, t] of Object.entries(i))
      this._downloadFile(e, t);
  }
  _resetWizard() {
    this._step = 1, this._preview = null, this._shareResult = null, this._error = "", this._customRedactionsInput = "", this._textOverrides = {}, this._confirmReviewItems = !1;
  }
  get _filteredItems() {
    const i = this._search.trim().toLowerCase();
    return this._items.filter((e) => this._domainFilter !== "all" && e.domain !== this._domainFilter ? !1 : i ? e.name.toLowerCase().includes(i) || e.entity_id.toLowerCase().includes(i) : !0);
  }
  render() {
    return c`
      <div class="page">
        <header class="header">
          <div class="header-inner">
            <div>
              <h1>Sharing Is Caring</h1>
              <p class="subtitle">
                Share automations &amp; scripts with all related helpers — zero sensitive data ever leaves Home Assistant.
              </p>
            </div>
            <div class="stepper" role="tablist" aria-label="Share workflow steps">
              <span class="step-pill ${this._step === 1 ? "active" : this._step > 1 ? "done" : ""}">
                1. Pick Ability
              </span>
              <span class="step-pill ${this._step === 2 ? "active" : this._step > 2 ? "done" : ""}">
                2. Privacy Audit
              </span>
              <span class="step-pill ${this._step === 3 ? "active" : ""}">
                3. Publish
              </span>
            </div>
          </div>
        </header>

        <main class="container">
          ${this._error ? c`<div class="alert alert-error" role="alert">${this._error}</div>` : d}

          ${this._step === 1 ? this._renderStep1() : d}
          ${this._step === 2 ? this._renderStep2() : d}
          ${this._step === 3 ? this._renderStep3() : d}
        </main>
      </div>
    `;
  }
  _renderStep1() {
    const i = this._filteredItems;
    return c`
      <section class="card">
        <div class="card-header">
          <h2>Select an Automation or Script</h2>
          <div class="filter-row">
            <input
              type="search"
              class="input"
              placeholder="Search automations & scripts..."
              .value=${this._search}
              @input=${(e) => {
      this._search = e.target.value;
    }}
            />
            <div class="pill-group">
              ${["all", "automation", "script"].map(
      (e) => c`
                  <button
                    class="pill-btn ${this._domainFilter === e ? "selected" : ""}"
                    @click=${() => {
        this._domainFilter = e;
      }}
                  >
                    ${e === "all" ? "All" : e === "automation" ? "Automations" : "Scripts"}
                  </button>
                `
    )}
            </div>
          </div>
        </div>

        ${this._loading && i.length === 0 ? c`<p class="muted">Loading automations and scripts...</p>` : i.length === 0 ? c`<p class="muted">No matching automations or scripts found.</p>` : c`
                <div class="entity-grid">
                  ${i.map(
      (e) => c`
                      <button
                        class="entity-card ${this._selectedEntityId === e.entity_id ? "selected" : ""}"
                        @click=${() => {
        this._selectedEntityId = e.entity_id, this._textOverrides = {};
      }}
                      >
                        <span class="badge badge-${e.domain}">${e.domain}</span>
                        <span class="entity-name">${e.name}</span>
                        <span class="entity-id">${e.entity_id}</span>
                      </button>
                    `
    )}
                </div>
              `}

        <div class="options-box">
          <h3>Bundle Options</h3>
          <div class="form-grid">
            <label class="field">
              <span>Public title override (optional)</span>
              <input
                type="text"
                class="input"
                placeholder="e.g. Smart Motion Hallway Light"
                .value=${this._titleOverride}
                @input=${(e) => {
      this._titleOverride = e.target.value;
    }}
              />
            </label>
            <label class="field">
              <span>Short description (optional)</span>
              <input
                type="text"
                class="input"
                placeholder="Briefly describe what this ability does"
                .value=${this._descriptionOverride}
                @input=${(e) => {
      this._descriptionOverride = e.target.value;
    }}
              />
            </label>
          </div>
          <div class="checkbox-row">
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this._includeCompanionScripts}
                @change=${(e) => {
      this._includeCompanionScripts = e.target.checked;
    }}
              />
              <span>Bundle referenced companion scripts</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this._generateBlueprint}
                @change=${(e) => {
      this._generateBlueprint = e.target.checked;
    }}
              />
              <span>Also generate parameterized Blueprint YAML</span>
            </label>
          </div>
        </div>

        <div class="actions-bar">
          <span class="muted">No data is uploaded during preview.</span>
          <button
            class="btn btn-primary"
            ?disabled=${!this._selectedEntityId || this._loading}
            @click=${() => void this._runPreview()}
          >
            ${this._loading ? "Analyzing & Sanitizing..." : "Inspect & Sanitize →"}
          </button>
        </div>
      </section>
    `;
  }
  _renderStep2() {
    if (!this._preview) return d;
    const { audit: i, dependencies: e, files: t } = this._preview, s = Object.keys(t), r = t[this._activeFileTab] ?? "";
    return c`
      <section class="card">
        <div class="audit-banner audit-${i.status}">
          <div>
            <strong>
              ${i.status === "clean" ? "Privacy Check Passed — Ready to Share" : i.status === "needs_review" ? `Review Required (${i.counts.needs_review} item(s))` : `Publishing Blocked (${i.counts.blocked} secret/blocker(s) detected)`}
            </strong>
            <p>
              Auto-redacted: ${i.counts.auto_redacted} · Needs review:
              ${i.counts.needs_review} · Blocked: ${i.counts.blocked}
            </p>
          </div>
          <code class="hash-pill" title="Exact SHA-256 preview hash verified at publish time">
            hash: ${this._preview.preview_hash.slice(0, 12)}
          </code>
        </div>

        <div class="dep-strip">
          <div class="dep-group">
            <strong>Bundled Helpers (${e.helpers.length})</strong>
            <div class="chip-list">
              ${e.helpers.length === 0 ? c`<span class="muted">None</span>` : e.helpers.map(
      (o) => c`<span class="chip">${o.entity_id}</span>`
    )}
            </div>
          </div>
          <div class="dep-group">
            <strong>Companion Scripts (${e.companion_scripts.length})</strong>
            <div class="chip-list">
              ${e.companion_scripts.length === 0 ? c`<span class="muted">None</span>` : e.companion_scripts.map(
      (o) => c`<span class="chip">${o.entity_id}</span>`
    )}
            </div>
          </div>
          <div class="dep-group">
            <strong>Anonymized External Roles (${e.external_roles.length})</strong>
            <div class="chip-list">
              ${e.external_roles.length === 0 ? c`<span class="muted">None</span>` : e.external_roles.map(
      (o) => c`<span class="chip chip-role">${o.placeholder_entity_id}</span>`
    )}
            </div>
          </div>
        </div>

        ${i.blocked.length > 0 ? c`
              <div class="findings-box findings-blocked">
                <h3>Blocked Findings (Must Resolve Before Publishing)</h3>
                <ul>
                  ${i.blocked.map(
      (o) => c`
                      <li>
                        <code>${o.location}</code> — ${o.message}
                      </li>
                    `
    )}
                </ul>
              </div>
            ` : d}

        ${i.needs_review.length > 0 ? c`
              <div class="findings-box findings-review">
                <h3>Items to Review</h3>
                <ul>
                  ${i.needs_review.map(
      (o) => c`
                      <li>
                        <div>
                          <code>${o.location}</code> — ${o.message}
                          ${o.snippet ? c`<div class="snippet">"${o.snippet}"</div>` : d}
                        </div>
                        ${o.category === "free_text_message" ? c`
                              <input
                                type="text"
                                class="input override-input"
                                placeholder="Optional replacement text (then click Re-Sanitize)"
                                .value=${this._textOverrides[o.location] ?? ""}
                                @input=${(a) => {
        const l = a.target.value;
        this._textOverrides = {
          ...this._textOverrides,
          [o.location]: l
        };
      }}
                              />
                            ` : d}
                      </li>
                    `
    )}
                </ul>
              </div>
            ` : d}

        <div class="redaction-bar">
          <label class="field flex-grow">
            <span>Extra custom words to redact everywhere (comma-separated)</span>
            <input
              type="text"
              class="input"
              placeholder="e.g. DogName, StreetName, MySSID"
              .value=${this._customRedactionsInput}
              @input=${(o) => {
      this._customRedactionsInput = o.target.value;
    }}
            />
          </label>
          <button
            class="btn btn-secondary"
            ?disabled=${this._loading}
            @click=${() => void this._runPreview()}
          >
            ${this._loading ? "Re-Sanitizing..." : "Re-Sanitize"}
          </button>
        </div>

        ${i.auto_redacted.length > 0 ? c`
              <details class="details-box">
                <summary>View ${i.auto_redacted.length} auto-redacted item(s)</summary>
                <ul>
                  ${i.auto_redacted.map(
      (o) => c`
                      <li>
                        <code>${o.location}</code> →
                        ${o.replacement ? c`<code>${o.replacement}</code>` : "stripped"}
                        (${o.message})
                      </li>
                    `
    )}
                </ul>
              </details>
            ` : d}

        <div class="code-viewer">
          <div class="tab-bar">
            <div class="tabs">
              ${s.map(
      (o) => c`
                  <button
                    class="tab-btn ${this._activeFileTab === o ? "active" : ""}"
                    @click=${() => {
        this._activeFileTab = o;
      }}
                  >
                    ${o}
                  </button>
                `
    )}
            </div>
            <div class="tab-actions">
              <button
                class="btn btn-small"
                @click=${() => void this._copyText(this._activeFileTab, r)}
              >
                ${this._copiedKey === this._activeFileTab ? "Copied!" : "Copy"}
              </button>
              <button
                class="btn btn-small"
                @click=${() => this._downloadFile(this._activeFileTab, r)}
              >
                Download
              </button>
            </div>
          </div>
          <pre class="code-pre"><code>${r}</code></pre>
        </div>

        <div class="actions-bar">
          <button class="btn btn-secondary" @click=${() => this._step = 1}>
            ← Back
          </button>
          <button
            class="btn btn-primary"
            ?disabled=${!i.can_publish || this._loading}
            @click=${() => this._step = 3}
          >
            Continue to Publish →
          </button>
        </div>
      </section>
    `;
  }
  _renderStep3() {
    var t;
    if (!this._preview) return d;
    const i = this._preview.audit.status === "needs_review", e = !!((t = this._status) != null && t.github_configured);
    return this._shareResult ? this._renderShareSuccess(this._shareResult) : c`
      <section class="card">
        <h2>Choose Share Destination</h2>
        <p class="muted">
          Only the exact sanitized bundle you reviewed (<code>${this._preview.preview_hash.slice(0, 12)}</code>) will be exported.
        </p>

        <div class="provider-grid">
          <button
            class="provider-card ${this._selectedProvider === "github_gist" ? "selected" : ""}"
            ?disabled=${!e}
            @click=${() => {
      this._selectedProvider = "github_gist";
    }}
          >
            <h3>GitHub Gist</h3>
            <p>
              ${e ? "Publish all bundle files to your GitHub account as a clean shareable URL." : "Not configured yet. Add your own GitHub PAT under Settings → Devices & Services → Sharing Is Caring → Reconfigure."}
            </p>
          </button>

          <button
            class="provider-card ${this._selectedProvider === "local" ? "selected" : ""}"
            @click=${() => {
      this._selectedProvider = "local";
    }}
          >
            <h3>Local Copy / Download</h3>
            <p>
              Zero cloud requests. Export and download all sanitized files directly to your device.
            </p>
          </button>
        </div>

        ${this._selectedProvider === "github_gist" && e ? c`
              <div class="visibility-box">
                <label class="field">
                  <span>Gist Visibility</span>
                  <select
                    class="input"
                    .value=${this._visibility}
                    @change=${(s) => {
      this._visibility = s.target.value;
    }}
                  >
                    <option value="secret">Secret (Unlisted — only people with the URL)</option>
                    <option value="public">Public (Listed on your GitHub profile)</option>
                  </select>
                </label>
              </div>
            ` : d}

        ${i ? c`
              <label class="checkbox-label confirm-box">
                <input
                  type="checkbox"
                  .checked=${this._confirmReviewItems}
                  @change=${(s) => {
      this._confirmReviewItems = s.target.checked;
    }}
                />
                <span>
                  I have inspected the ${this._preview.audit.counts.needs_review} item(s) marked
                  <strong>Needs Review</strong> and confirmed no personal data remains.
                </span>
              </label>
            ` : d}

        <div class="actions-bar">
          <button class="btn btn-secondary" @click=${() => this._step = 2}>
            ← Back to Preview
          </button>
          <button
            class="btn btn-primary"
            ?disabled=${this._loading || i && !this._confirmReviewItems}
            @click=${() => void this._publishBundle()}
          >
            ${this._loading ? "Publishing..." : this._selectedProvider === "github_gist" ? "Publish Sanitized Gist" : "Export Locally"}
          </button>
        </div>
      </section>
    `;
  }
  _renderShareSuccess(i) {
    return c`
      <section class="card">
        <div class="audit-banner audit-clean">
          <div>
            <strong>Sanitized Ability Ready!</strong>
            <p>
              ${i.share_url ? `Published to GitHub Gist (${i.visibility}).` : "Sanitized bundle exported locally (zero external requests made)."}
            </p>
          </div>
        </div>

        ${i.share_url ? c`
              <div class="url-row">
                <label class="field flex-grow">
                  <span>Shareable URL</span>
                  <input type="text" class="input" readonly .value=${i.share_url} />
                </label>
                <button
                  class="btn btn-primary"
                  @click=${() => void this._copyText("share_url", i.share_url ?? "")}
                >
                  ${this._copiedKey === "share_url" ? "Copied!" : "Copy URL"}
                </button>
                <a
                  class="btn btn-secondary"
                  href=${i.share_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open
                </a>
              </div>
            ` : d}

        ${i.my_ha_import_url ? c`
              <div class="url-row">
                <label class="field flex-grow">
                  <span>1-Click My Home Assistant Blueprint Import URL</span>
                  <input type="text" class="input" readonly .value=${i.my_ha_import_url} />
                </label>
                <button
                  class="btn btn-secondary"
                  @click=${() => void this._copyText("my_ha_url", i.my_ha_import_url ?? "")}
                >
                  ${this._copiedKey === "my_ha_url" ? "Copied!" : "Copy Import Link"}
                </button>
              </div>
            ` : d}

        <div class="actions-bar">
          <button
            class="btn btn-secondary"
            @click=${() => this._downloadAllFiles(i.files)}
          >
            Download All Files
          </button>
          <button class="btn btn-primary" @click=${() => this._resetWizard()}>
            Share Another Ability
          </button>
        </div>
      </section>
    `;
  }
};
p.styles = be`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color, #fafafa);
      color: var(--primary-text-color, #212121);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }

    .header {
      background: var(--app-header-background-color, var(--primary-color, #03a9f4));
      color: var(--app-header-text-color, #ffffff);
      padding: 20px 24px;
    }

    .header-inner {
      max-width: 1120px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 500;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 1.2rem;
    }

    h3 {
      margin: 0 0 8px;
      font-size: 1rem;
    }

    .subtitle {
      margin: 4px 0 0;
      opacity: 0.9;
      font-size: 0.92rem;
    }

    .stepper {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .step-pill {
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.16);
      font-size: 0.85rem;
    }

    .step-pill.active {
      background: #ffffff;
      color: var(--primary-color, #03a9f4);
      font-weight: 600;
    }

    .step-pill.done {
      background: rgba(255, 255, 255, 0.32);
    }

    .container {
      max-width: 1120px;
      margin: 24px auto;
      padding: 0 16px 40px;
    }

    .card {
      background: var(--card-background-color, #ffffff);
      border-radius: var(--ha-card-border-radius, 12px);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      padding: 20px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.06));
    }

    .alert {
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .alert-error {
      background: rgba(219, 68, 55, 0.12);
      border: 1px solid var(--error-color, #db4437);
      color: var(--error-color, #db4437);
    }

    .filter-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 16px;
      align-items: center;
    }

    .input {
      width: 100%;
      box-sizing: border-box;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.22));
      background: var(--primary-background-color, #ffffff);
      color: var(--primary-text-color, #212121);
      font-size: 0.95rem;
    }

    .filter-row .input {
      flex: 1 1 260px;
    }

    .pill-group {
      display: flex;
      gap: 6px;
    }

    .pill-btn {
      padding: 7px 14px;
      border-radius: 999px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.2));
      background: transparent;
      color: inherit;
      cursor: pointer;
    }

    .pill-btn.selected {
      background: var(--primary-color, #03a9f4);
      border-color: var(--primary-color, #03a9f4);
      color: #ffffff;
    }

    .entity-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 10px;
      max-height: 320px;
      overflow-y: auto;
      padding: 4px 2px;
    }

    .entity-card {
      text-align: left;
      padding: 12px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      background: var(--primary-background-color, #fafafa);
      color: inherit;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .entity-card.selected {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.25);
    }

    .badge {
      align-self: flex-start;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(3, 169, 244, 0.15);
      color: var(--primary-color, #03a9f4);
    }

    .badge-script {
      background: rgba(156, 39, 176, 0.14);
      color: #9c27b0;
    }

    .entity-name {
      font-weight: 500;
    }

    .entity-id,
    .muted {
      font-size: 0.85rem;
      color: var(--secondary-text-color, #666666);
    }

    .options-box {
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.88rem;
    }

    .flex-grow {
      flex: 1 1 300px;
    }

    .checkbox-row {
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-top: 8px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-size: 0.92rem;
    }

    .audit-banner {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-radius: 10px;
      margin-bottom: 16px;
    }

    .audit-banner p {
      margin: 4px 0 0;
      font-size: 0.88rem;
    }

    .audit-clean {
      background: rgba(67, 160, 71, 0.14);
      border: 1px solid var(--success-color, #43a047);
    }

    .audit-needs_review {
      background: rgba(255, 152, 0, 0.15);
      border: 1px solid var(--warning-color, #ff9800);
    }

    .audit-blocked {
      background: rgba(219, 68, 55, 0.15);
      border: 1px solid var(--error-color, #db4437);
    }

    .hash-pill {
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(0, 0, 0, 0.08);
      font-size: 0.82rem;
    }

    .dep-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .dep-group {
      padding: 12px;
      border-radius: 8px;
      background: var(--primary-background-color, #f5f5f5);
      font-size: 0.88rem;
    }

    .chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .chip {
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(3, 169, 244, 0.12);
      font-family: monospace;
      font-size: 0.8rem;
    }

    .chip-role {
      background: rgba(103, 58, 183, 0.12);
    }

    .findings-box {
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .findings-box ul {
      margin: 8px 0 0;
      padding-left: 20px;
    }

    .findings-box li {
      margin-bottom: 8px;
    }

    .findings-blocked {
      background: rgba(219, 68, 55, 0.1);
      border-left: 4px solid var(--error-color, #db4437);
    }

    .findings-review {
      background: rgba(255, 152, 0, 0.1);
      border-left: 4px solid var(--warning-color, #ff9800);
    }

    .snippet {
      margin-top: 4px;
      font-family: monospace;
      font-size: 0.85rem;
      opacity: 0.85;
    }

    .override-input {
      margin-top: 6px;
    }

    .redaction-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-end;
      margin-bottom: 14px;
    }

    .details-box {
      margin-bottom: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      background: var(--primary-background-color, #f5f5f5);
      font-size: 0.88rem;
    }

    .details-box summary {
      cursor: pointer;
      font-weight: 500;
    }

    .code-viewer {
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 16px;
    }

    .tab-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      background: var(--primary-background-color, #f0f0f0);
      padding: 6px 10px;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }

    .tabs,
    .tab-actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .tab-btn {
      padding: 6px 12px;
      border: none;
      border-radius: 6px;
      background: transparent;
      color: inherit;
      cursor: pointer;
      font-family: monospace;
      font-size: 0.85rem;
    }

    .tab-btn.active {
      background: var(--card-background-color, #ffffff);
      font-weight: 600;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .code-pre {
      margin: 0;
      padding: 14px;
      max-height: 420px;
      overflow: auto;
      font-size: 0.84rem;
      line-height: 1.45;
      background: var(--code-editor-background-color, #1e1e1e);
      color: #e6e6e6;
    }

    .provider-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }

    .provider-card {
      text-align: left;
      padding: 16px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      background: var(--primary-background-color, #fafafa);
      color: inherit;
      cursor: pointer;
    }

    .provider-card.selected {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.25);
    }

    .provider-card:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .visibility-box,
    .confirm-box {
      margin: 14px 0;
    }

    .confirm-box {
      padding: 12px;
      border-radius: 8px;
      background: rgba(255, 152, 0, 0.12);
    }

    .url-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-end;
      margin-bottom: 14px;
    }

    .actions-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
    }

    .btn {
      padding: 9px 18px;
      border-radius: 8px;
      border: none;
      font-size: 0.92rem;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-primary {
      background: var(--primary-color, #03a9f4);
      color: #ffffff;
    }

    .btn-secondary {
      background: var(--secondary-background-color, #e0e0e0);
      color: var(--primary-text-color, #212121);
    }

    .btn-small {
      padding: 5px 10px;
      font-size: 0.8rem;
      background: var(--card-background-color, #ffffff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      color: inherit;
    }
  `;
u([
  Z({ attribute: !1 })
], p.prototype, "hass", 2);
u([
  Z({ type: Boolean })
], p.prototype, "narrow", 2);
u([
  _()
], p.prototype, "_step", 2);
u([
  _()
], p.prototype, "_loading", 2);
u([
  _()
], p.prototype, "_error", 2);
u([
  _()
], p.prototype, "_copiedKey", 2);
u([
  _()
], p.prototype, "_status", 2);
u([
  _()
], p.prototype, "_items", 2);
u([
  _()
], p.prototype, "_search", 2);
u([
  _()
], p.prototype, "_domainFilter", 2);
u([
  _()
], p.prototype, "_selectedEntityId", 2);
u([
  _()
], p.prototype, "_titleOverride", 2);
u([
  _()
], p.prototype, "_descriptionOverride", 2);
u([
  _()
], p.prototype, "_includeCompanionScripts", 2);
u([
  _()
], p.prototype, "_generateBlueprint", 2);
u([
  _()
], p.prototype, "_preview", 2);
u([
  _()
], p.prototype, "_activeFileTab", 2);
u([
  _()
], p.prototype, "_customRedactionsInput", 2);
u([
  _()
], p.prototype, "_textOverrides", 2);
u([
  _()
], p.prototype, "_selectedProvider", 2);
u([
  _()
], p.prototype, "_visibility", 2);
u([
  _()
], p.prototype, "_confirmReviewItems", 2);
u([
  _()
], p.prototype, "_shareResult", 2);
p = u([
  ze("sharing-is-caring-panel")
], p);
export {
  p as SharingIsCaringPanel
};
