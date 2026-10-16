import json
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class PortfolioHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.landmarks = []
        self.heading_levels = []
        self.images = []
        self.styles = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if tag in {"nav", "main", "section", "article", "footer"}:
            self.landmarks.append(tag)
        if re.fullmatch(r"h[1-6]", tag):
            self.heading_levels.append(int(tag[1]))
        if tag == "img":
            self.images.append(attributes)
        if tag == "link":
            self.styles.append(attributes)
        if tag == "script":
            self.scripts.append(attributes)


class PortfolioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = INDEX.read_text(encoding="utf-8")
        cls.document = PortfolioHTML()
        cls.document.feed(cls.source)
        body_match = re.search(r"<body[^>]*>(.*)</body>", cls.source, flags=re.DOTALL)
        cls.body_source = body_match.group(1) if body_match else cls.source
        cls.normalized_text = " ".join(cls.source.split()).lower()

    def test_required_sections_exist(self):
        self.assertTrue(
            {
                "top",
                "impact",
                "recruiter-profile",
                "gpu-story",
                "current-work",
                "experience",
                "evidence",
                "contact",
            }
            <= self.document.ids
        )

    def test_cv_download_is_linked_and_present(self):
        cv_path = "assets/zurab-khadikov-lebenslauf.pdf"
        self.assertIn(cv_path, self.document.links)
        self.assertTrue((ROOT / cv_path).is_file())
        self.assertIn(f'href="{cv_path}" download', self.source)

    def test_published_cv_has_no_private_contact_details(self):
        cv_bytes = (ROOT / "assets/zurab-khadikov-lebenslauf.pdf").read_bytes()
        self.assertNotIn(b"mailto:", cv_bytes)
        self.assertNotIn(b"tel:", cv_bytes)

    def test_architecture_certification_is_listed(self):
        for phrase in (
            "certified professional for software architecture",
            "foundation level",
            "isaqb",
            "2101-cpsafl-201863-de",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_text)

    def test_recruiter_profile_is_explicit(self):
        required_phrases = (
            "principal software architect",
            "engineering leadership",
            "industrial ai architect",
            "15+ years",
            "freiburg",
            "core competencies",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_text)

    def test_signature_story_contains_verified_milestones(self):
        required_phrases = (
            "bachelor",
            "cuda",
            "2009",
            "nvidia tesla",
            "jedox gpu accelerator",
            "commercial",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_text)

    def test_performance_claims_are_contextualized(self):
        for phrase in ("prototype", "research", "commercial", "current documentation", "workload-dependent"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_text)
        for metric in ("4.8", "18", "50", "150", "5–10", "70"):
            with self.subTest(metric=metric):
                self.assertIn(metric, self.source)

    def test_private_information_is_not_published(self):
        # Do not include raw private identifiers (emails, phone numbers, or DOBs).
        # Use structural checks instead of embedding real private literals.
        # Ensure there are no raw email addresses
        self.assertIsNone(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", self.source))
        # Ensure there are no international-style phone numbers like +49 ...
        self.assertIsNone(re.search(r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?", self.source))
        # Ensure there are no explicit dates in common dd.mm.yyyy or dd/mm/yyyy formats
        self.assertIsNone(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", self.source))
        # Ensure family/marital status is not published as explicit personal claims
        self.assertNotIn("verheirat", self.normalized_text)
        # Do not publish explicit family details like 'child' or 'children' as whole words
        self.assertIsNone(re.search(r"\bchild(?:ren)?\b", self.normalized_text))
        # Naive detection of street addresses by common street-type words
        self.assertIsNone(re.search(r"\b(?:strasse|straße|street|weg|allee|platz|road|lane|st|rd)\b", self.normalized_text))

    def test_required_public_sources_are_linked(self):
        required_links = {
            "https://knowledgebase-onprem.jedox.com/on-prem/gpu-accelerator.htm",
            "https://knowledgebase-onprem.jedox.com/on-prem/gpu-accelerator-faq.htm",
            "https://www.jedox.com/en/about/company/",
            "https://www.nvidia.com/content/GTC/posters/75_Lauer_Palo_Plus_GPU.pdf",
            "https://doi.org/10.1145/1871940.1871958",
            "https://patents.google.com/patent/US11644827B2/en",
        }
        self.assertTrue(required_links <= set(self.document.links))

    def test_page_uses_semantic_landmarks(self):
        for landmark in ("nav", "main", "section", "article", "footer"):
            with self.subTest(landmark=landmark):
                self.assertIn(landmark, self.document.landmarks)

    def test_images_have_alt_text_and_dimensions(self):
        self.assertGreater(len(self.document.images), 0)
        for image in self.document.images:
            self.assertTrue(image.get("alt"))
            self.assertTrue(image.get("width"))
            self.assertTrue(image.get("height"))

    def test_hero_uses_local_optimized_portrait(self):
        portrait = next(
            (image for image in self.document.images
             if image.get("src") == "assets/zurab-khadikov.webp"),
            None,
        )
        self.assertIsNotNone(portrait, "Hero portrait not found; expected a local optimized portrait at assets/zurab-khadikov.webp")
        self.assertEqual("eager", portrait.get("loading"))
        self.assertEqual("high", portrait.get("fetchpriority"))

    def test_site_has_no_external_stylesheets_or_scripts(self):
        external_styles = [
            item for item in self.document.styles
            if item.get("rel") == "stylesheet" and item.get("href", "").startswith("http")
        ]
        external_scripts = [
            item for item in self.document.scripts
            if item.get("src", "").startswith("http")
        ]
        self.assertEqual([], external_styles)
        self.assertEqual([], external_scripts)

    def test_json_ld_is_valid_and_recruiter_readable(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.source,
            flags=re.DOTALL,
        )
        self.assertEqual(1, len(blocks))
        graph = json.loads(blocks[0])
        self.assertEqual("https://schema.org", graph["@context"])
        entities = graph["@graph"]
        person = next(item for item in entities if item["@type"] == "Person")
        self.assertEqual("Zurab Khadikov", person["name"])
        self.assertEqual("https://zkhadikov.github.io/", person["url"])
        self.assertEqual("https://zkhadikov.github.io/assets/zurab-khadikov.webp", person["image"])
        self.assertIn("Senior Software Architect", person["jobTitle"])
        self.assertNotIn("homeLocation", person)
        self.assertEqual("Freiburg, Germany", person["workLocation"]["name"])
        self.assertIn(person["workLocation"]["name"], self.body_source)
        self.assertGreaterEqual(len(person["hasOccupation"]), 3)
        self.assertGreaterEqual(len(person["knowsAbout"]), 10)
        self.assertGreaterEqual(len(person["hasCredential"]), 2)
        self.assertGreaterEqual(len(person["sameAs"]), 3)
        self.assertNotIn("subjectOf", person)
        for role in person["jobTitle"]:
            with self.subTest(role=role):
                self.assertIn(role, self.body_source)
        for topic in person["knowsAbout"]:
            with self.subTest(topic=topic):
                self.assertIn(topic, self.body_source)

        article = next(item for item in entities if item["@type"] == "ScholarlyArticle")
        self.assertEqual(4, len(article["author"]))
        self.assertIn({"@id": "https://zkhadikov.github.io/#person"}, article["author"])
        self.assertEqual(
            {"Tobias Lauer", "Amitava Datta", "Christoffer Anselm"},
            {author["name"] for author in article["author"] if "name" in author},
        )
        patent = next(item for item in entities if item["@type"] == "CreativeWork")
        self.assertEqual(7, len(patent["contributor"]))
        self.assertIn(
            {"@id": "https://zkhadikov.github.io/#person"},
            patent["contributor"],
        )
        self.assertEqual(
            {
                "Manfred Niederer",
                "Stefan Robl",
                "Ervin Binkert",
                "Alexey Malinovskiy",
                "Heiko Oehme",
                "Ulrich Kaiser",
            },
            {
                contributor["name"]
                for contributor in patent["contributor"]
                if "name" in contributor
            },
        )

        entity_types = {item["@type"] for item in entities}
        self.assertTrue(
            {
                "Person",
                "Occupation",
                "EducationalOccupationalCredential",
                "ScholarlyArticle",
                "CreativeWork",
            }
            <= entity_types
        )

    def test_metadata_supports_recruiting_discovery(self):
        for value in (
            '<link rel="canonical" href="https://zkhadikov.github.io/">',
            'property="og:title"',
            'property="og:description"',
            'property="og:image" content="https://zkhadikov.github.io/assets/zurab-khadikov-social.jpg"',
            'name="twitter:card"',
            'name="twitter:image" content="https://zkhadikov.github.io/assets/zurab-khadikov-social.jpg"',
            "Principal Software Architect",
            "Agentic AI Architect",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.source)

        for value in (
            '<time datetime="2008">2008</time>–<time datetime="2009">2009</time>',
            '<time datetime="2009">2009</time>–<time datetime="2012">2012</time>',
            '<time datetime="2010">2010</time>',
            '<time datetime="2023">2023</time>',
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.source)

    def test_accessibility_css_contract(self):
        for rule in (
            ":focus-visible",
            "@media (prefers-reduced-motion: reduce)",
            "scroll-margin-top",
            "main#top",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.source)

    def test_responsive_css_contract(self):
        self.assertIn("@media (max-width:", self.source)
        self.assertIn("minmax(0, 1fr)", self.source)
        self.assertIn("overflow-wrap:", self.source)

    def test_approved_visual_tokens_exist(self):
        for token in (
            "--color-bg:",
            "--color-panel:",
            "--color-text:",
            "--color-muted:",
            "--color-accent:",
            "--color-line:",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.source)

    def test_proof_strip_metrics_use_monospace(self):
        self.assertIn(".metric {", self.source)
        self.assertIn("font-family: var(--font-mono);", self.source)

    def test_progressive_enhancement_contract(self):
        for value in (
            "IntersectionObserver",
            'class="brand" href="#top"',
            '<section id="top" class="hero"',
            "const intersectionState = new Map();",
            "intersectionState.set(entry.target",
            '[...intersectionState.entries()]',
            'link.removeAttribute("aria-current")',
            'data-filter="all"',
            "data-tags=",
            "aria-pressed",
            ".enhanced .filters {",
            "prefers-reduced-motion: reduce",
            'root.classList.add("enhanced")',
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.source)
        self.assertRegex(
            self.source,
            r"\.filters\s*\{\s*display:\s*none;",
        )

    def test_enhancement_does_not_fetch_or_inject_profile_content(self):
        self.assertNotIn("fetch(", self.source)
        self.assertNotIn(".innerHTML", self.source)

    def test_gpu_evidence_uses_native_disclosures(self):
        self.assertIn("<details", self.source)
        self.assertIn("<summary", self.source)


if __name__ == "__main__":
    unittest.main()
