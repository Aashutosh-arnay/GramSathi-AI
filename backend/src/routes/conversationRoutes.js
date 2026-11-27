
const express = require("express");
const router = express.Router();

const {
  createConversation,
  getConversations,
  getConversationById,
  deleteConversation
} = require("../controllers/conversationController");

const {
  getMessages,
  addMessage
} = require("../controllers/messageController");
const { protect } = require("../middleware/authMiddleware");

// Create a new conversation
router.post("/", protect, createConversation);
router.get("/", protect, getConversations);
router.get("/:id", protect, getConversationById);
router.delete("/:id", protect, deleteConversation);
// Add user message
router.post("/:id/messages", protect, addMessage);

// Get conversation messages
router.get("/:id/messages", protect, getMessages);

module.exports = router;
