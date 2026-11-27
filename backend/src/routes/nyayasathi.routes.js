
const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/authMiddleware");

const {
    askNyayaSathiController
} = require("../controllers/nyayasathi.controller");

router.post("/ask", protect, askNyayaSathiController);

module.exports = router;
