import heroGirl from "../images/heroGirl.jpeg";
import eye from "../images/eye.jpeg";
import thirdImage from "../images/thirdImage.png";

export const IMAGES = {
  heroGirl: heroGirl,
  eye: eye,
  thirdImage: thirdImage
};

export const EVENT_START = "2026-11-27T09:00:00+05:30";

export const TRACKS = [
  { code: "01", key: "drone", icon: "Crosshair", short: "Defence AI",
    title: "AI-Enabled Drone & Counter-Drone Threat Simulation Trainer",
    value: "AI-Enabled Drone & Counter-Drone Threat Simulation Trainer",
    desc: "Explore AI-driven simulation and training systems designed to study drone-related threats and improve threat-response preparedness." },
  { code: "02", key: "food", icon: "Leaf", short: "Sustainability",
    title: "AI-Powered Smart Food Waste Reduction & Sustainable Redistribution Ecosystem",
    value: "AI-Powered Smart Food Waste Reduction & Sustainable Redistribution Ecosystem",
    desc: "Develop intelligent solutions for institutional kitchens and food processing units to reduce food waste and support sustainable redistribution." },
  { code: "03", key: "v2v", icon: "Car", short: "Mobility",
    title: "V2V Visionaries: Collision Avoidance & Road Safety",
    value: "V2V Visionaries: Collision Avoidance & Road Safety",
    desc: "Reimagine safer roads through vehicle-to-vehicle communication, intelligent sensing, and next-generation collision avoidance solutions." },
  { code: "04", key: "stethoscope", icon: "HeartPulse", short: "HealthTech",
    title: "Edge-AI Smart Stethoscope for Real-Time Cardiopulmonary Screening in Rural PHCs",
    value: "Edge-AI Smart Stethoscope for Cardiopulmonary Screening",
    desc: "Explore smart, edge-enabled stethoscope systems that support preliminary cardiopulmonary screening in rural Primary Health Centres." },
  { code: "05", key: "sanitation", icon: "Recycle", short: "Sanitation",
    title: "On-Site Containment-Based Toilets: Sustainable Waste Treatment",
    value: "On-Site Containment-Based Toilets",
    desc: "Technological, biochemical, or nature-based approaches for treating excreta on-site while protecting the environment and groundwater." },
  { code: "06", key: "water", icon: "Droplets", short: "Smart Infra",
    title: "Indigenous Leak Detection Sensor Systems for Water Supply Pipelines",
    value: "Indigenous Water Pipeline Leak Detection Sensors",
    desc: "Develop indigenous sensor-based systems for detecting pipeline leaks and improving water-supply operation and maintenance." },
];

export const PHASES = [
  { n: "01", date: "10 NOV", until: "2026-11-10T23:59:00+05:30", title: "Abstract submission closes", sub: "Submit a one-page abstract for one of six themes" },
  { n: "02", date: "15 NOV", until: "2026-11-15T23:59:00+05:30", title: "Acceptance notifications", sub: "Mentors shortlist the boldest ideas" },
  { n: "03", date: "16–25 NOV", until: "2026-11-25T23:59:00+05:30", title: "Final team registration", sub: "₹600 per shortlisted team" },
  { n: "04", date: "27–28 NOV", until: "2026-11-28T23:59:00+05:30", title: "SANKALP'26 goes live", sub: "24 hours of build at AJIET, Mangaluru" },
];

export const WHY = [
  { icon: "Zap", title: "Rapid prototyping", text: "Turn raw concepts into practical demos in one intense 24-hour sprint." },
  { icon: "Users", title: "Mentor support", text: "Guidance, feedback and direction from industry and academic mentors." },
  { icon: "Globe2", title: "Real-world impact", text: "Build for sustainability, AI, healthcare, mobility and smart communities." },
  { icon: "Trophy", title: "Exposure & rewards", text: "Showcase your idea on a national stage and compete for ₹75,000." },
];

export const STORY = [
  { n: "01", tag: "THE SPARK", title: "Ideas Today.", text: "She was human first — restless, curious, unafraid to ask why. Every revolution starts as a whisper inside someone like her. Sankalp (संकल्प) is that whisper: a solemn resolve to build what doesn't exist yet." },
  { n: "02", tag: "THE CIRCUIT", title: "24 hours. One resolve.", text: "Code becomes nerve. Solder becomes skin. For twenty-four hours, ideas rewire into prototypes and teams become a single circuit — humming cyan, burning rose." },
  { n: "03", tag: "THE AWAKENING", title: "A Brighter Tomorrow.", text: "When she opens her eyes, the world is a little safer, cleaner, healthier. That is the promise of SANKALP'26 — Build. Breakthrough. Belong." },
];

export const HOSTS = [
  { name: "IEEE Mangalore Subsection", role: "Supported by" },
  { name: "A J Institute of Engineering & Technology", role: "Host institution" },
  { name: "IEEE AJIET Student Branch", role: "Organiser" },
  { name: "Dept. of ECE, AJIET", role: "In association with" },
];

export const SPONSORS = [
  { name: "BRAVYNEX ENGINEERING", sub: "Cultivating Success Together", color: "#c65bff" },
  { name: "Binary Waves", sub: "connect & communicate", color: "#3fa2ff" },
];

export const TEAM = [
  { group: "Patrons", people: [["Dr. A.J. Shetty", "President, LMET"], ["Mr. Prashanth Shetty", "Vice-President, LMET"]] },
  { group: "Advisory committee", people: [["Dr. Jayaprakash Rao T", "Campus Director"], ["Dr. Ashok Kumar T", "Principal"], ["Dr. Shantharama Rai C", "Dean (R&D)"]] },
  { group: "Chief coordinator", people: [["Dr. Kiran Kumar V G", "HoD – ECE"]] },
  { group: "Faculty coordinators", people: [["Prof. Rohith Kumar", "Skill Development Cell"], ["Prof. Manjukiran B", "Faculty Coordinator"], ["Prof. Pratheeksha N Rai", "Faculty Coordinator"]] },
  { group: "Student coordinators", people: [["Ms. Pranamya Shetty", "+91 9632527739"], ["Mr. Yashas Shetty", "+91 9110216295"], ["Ms. S. Asha", "+91 7795371412"]] },
];

export const FAQS = [
  ["Who can participate?", "Students pursuing BE/BTech, MCA and Diploma programs from any institution across India."],
  ["What is the team size?", "Each team may include up to 3 members. Provide the complete name, USN and email for every member."],
  ["How do I get shortlisted?", "Choose one of the six problem statements and submit a one-page abstract (problem, proposed solution, approach, impact) by 10 November 2026. Industry and academic mentors evaluate abstracts and notify shortlisted teams by 15 November."],
  ["Is there a registration fee?", "Abstract submission is free. Shortlisted teams pay a final registration fee of ₹600 per team between 16 and 25 November 2026."],
  ["What do we submit on this portal?", "Your project title, description, GitHub repository, live demo link, video pitch (YouTube/Drive), tech stack and chosen problem statement. You can edit it until submissions lock for evaluation."],
  ["How is judging done?", "Judges score every project on Innovation, Technical depth, Feasibility and Presentation (10 points each). Scores are averaged across judges and ranked live on the leaderboard."],
  ["Where is the event?", "A.J. Institute of Engineering and Technology, NH-66, Kottara Chowki, Mangaluru, Karnataka."],
  ["Who do I contact?", "Email hackathon@ajiet.edu.in, or call Prof. Manjukiran B (+91 8197278959) or Ms. Pranamya Shetty (+91 9632527739)."],
];
