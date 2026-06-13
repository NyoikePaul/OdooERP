/* ArtBeat Studio — main.js v3 | Naivasha */

// ── NAV + TOPBAR SCROLL ──────────────────────
const nav = document.getElementById('nav');
const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 40);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

// ── MOBILE MENU ──────────────────────────────
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');
navToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', open);
  const [s1,s2,s3] = navToggle.querySelectorAll('span');
  if (open) {
    s1.style.transform = 'translateY(7px) rotate(45deg)';
    s2.style.opacity   = '0';
    s3.style.transform = 'translateY(-7px) rotate(-45deg)';
  } else {
    [s1,s2,s3].forEach(s => { s.style.transform=''; s.style.opacity=''; });
  }
});
navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  navLinks.classList.remove('open');
  navToggle.querySelectorAll('span').forEach(s => { s.style.transform=''; s.style.opacity=''; });
}));

// ── HERO SLIDESHOW ───────────────────────────
const SLIDE_DURATION = 5500;
const slides      = Array.from(document.querySelectorAll('.slide'));
const dots        = Array.from(document.querySelectorAll('.dot'));
const progressBar = document.getElementById('slideProgressBar');
let current = 0, timer = null;

function goTo(idx) {
  slides[current].classList.remove('active');
  dots[current].classList.remove('active');
  current = ((idx % slides.length) + slides.length) % slides.length;
  slides[current].classList.add('active');
  dots[current].classList.add('active');

  // Progress bar reset & animate
  progressBar.style.transition = 'none';
  progressBar.style.width = '0%';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    progressBar.style.transition = `width ${SLIDE_DURATION}ms linear`;
    progressBar.style.width = '100%';
  }));

  clearTimeout(timer);
  timer = setTimeout(() => goTo(current + 1), SLIDE_DURATION);
}

// Init slideshow
goTo(0);
document.getElementById('slideNext').addEventListener('click', () => goTo(current + 1));
document.getElementById('slidePrev').addEventListener('click', () => goTo(current - 1));
dots.forEach(d => d.addEventListener('click', () => goTo(+d.dataset.slide)));

// Touch/swipe support
let touchX = 0;
const hero = document.querySelector('.hero');
hero.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
hero.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) goTo(dx < 0 ? current + 1 : current - 1);
}, { passive: true });

// Keyboard
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') goTo(current + 1);
  if (e.key === 'ArrowLeft')  goTo(current - 1);
});

// Pause on hover
hero.addEventListener('mouseenter', () => clearTimeout(timer));
hero.addEventListener('mouseleave', () => { clearTimeout(timer); timer = setTimeout(() => goTo(current+1), SLIDE_DURATION); });

// ── SCROLL REVEAL ────────────────────────────
const revealObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); revealObs.unobserve(e.target); }
  });
}, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal').forEach((el, i) => {
  el.style.transitionDelay = `${(i % 4) * 0.09}s`;
  revealObs.observe(el);
});

// ── STATS COUNTER ────────────────────────────
function counter(el, target, suffix='') {
  let start = null;
  const step = ts => {
    if (!start) start = ts;
    const p = Math.min((ts - start) / 1800, 1);
    const v = Math.floor((1 - Math.pow(1-p, 3)) * target);
    el.textContent = v + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
const trustObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.querySelectorAll('.trust-n').forEach(el => {
      const t = el.textContent;
      const num = parseInt(t.replace(/\D/g,''));
      const suf = t.replace(/[\d,]/g,'');
      if (!isNaN(num) && num > 0) counter(el, num, suf);
    });
    trustObs.unobserve(e.target);
  });
}, { threshold: 0.5 });
const trustBar = document.querySelector('.trust-bar');
if (trustBar) trustObs.observe(trustBar);

// ── CONTACT FORM ─────────────────────────────
document.getElementById('contactForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone')?.value.trim() || '';
  const service = document.getElementById('service').value;
  const message = document.getElementById('message').value.trim();

  // Basic validation
  if (!name || !service || !message) {
    btn.textContent = '⚠ Please fill required fields';
    btn.style.background = '#b91c1c';
    setTimeout(() => { btn.textContent = 'Send Enquiry ✦'; btn.style.background = ''; }, 3000);
    return;
  }

  btn.textContent = 'Sending…';
  btn.disabled = true;

  // Build WhatsApp fallback URL
  const waText = encodeURIComponent(
    `Hello ArtBeat Studio!\n\nName: ${name}\nPhone: ${phone}\nService: ${service}\n\nMessage: ${message}`
  );
  const waUrl = `https://wa.me/254114663650?text=${waText}`;

  await new Promise(r => setTimeout(r, 1200));
  btn.textContent = '✓ Sent! Opening WhatsApp…';
  btn.style.background = '#16a34a';
  e.target.reset();

  setTimeout(() => {
    window.open(waUrl, '_blank');
    btn.textContent = 'Send Enquiry ✦';
    btn.style.background = '';
    btn.disabled = false;
  }, 1500);
});

// ── ACTIVE NAV ───────────────────────────────
const sectionEls = document.querySelectorAll('section[id]');
const navAnchors = document.querySelectorAll('.nav-links a[href^="#"]');
const activeObs  = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      navAnchors.forEach(a => {
        a.style.color = a.getAttribute('href') === `#${e.target.id}` ? 'var(--gold)' : '';
      });
    }
  });
}, { threshold: 0.35 });
sectionEls.forEach(s => activeObs.observe(s));

// ── GALLERY OVERLAY (touch devices) ──────────
document.querySelectorAll('.gallery-item').forEach(item => {
  item.addEventListener('touchstart', () => {
    document.querySelectorAll('.gallery-item').forEach(i => i.classList.remove('touch-active'));
    item.classList.add('touch-active');
  }, { passive: true });
});
