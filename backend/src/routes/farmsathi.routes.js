
const express = require("express");
const router = express.Router();

const { protect } = require("../middleware/authMiddleware");

const {
    askFarmSathiController
} = require("../controllers/farmsathi.controller");

router.post("/ask", protect, askFarmSathiController);

module.exports = router;
