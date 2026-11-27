
const express = require("express");
const router = express.Router();

const {
  registerUser,
  loginUser,
  getMe,
  updateMe,
  changePassword,
} = require("../controllers/authController");

const { protect } = require("../middleware/authMiddleware");

// User Registration
router.post("/register", registerUser);

// User Login
router.post("/login", loginUser);

// Get Current User Profile
router.get("/me", protect, getMe);

// Update User Profile
router.patch("/me", protect, updateMe);

// Change Password
router.patch("/change-password", protect, changePassword);

module.exports = router;
