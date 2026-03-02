#!/usr/bin/env node
/**
 * Email MCP Server
 * Provides email sending capabilities via the Model Context Protocol
 * Part of the Personal AI Employee Silver Tier implementation
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import nodemailer from 'nodemailer';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const VAULT_BASE = join(__dirname, '..', 'AI_Employee_Vault');
const LOGS_DIR = join(VAULT_BASE, 'Logs');
const DONE_DIR = join(VAULT_BASE, 'Done');

// Ensure directories exist
if (!fs.existsSync(LOGS_DIR)) {
  fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// Logger
function log(level, message) {
  const timestamp = new Date().toISOString();
  const logLine = `${timestamp} - ${level} - ${message}\n`;
  console.error(logLine.trim());
  
  // Also write to log file
  const logFile = join(LOGS_DIR, 'email_mcp.log');
  fs.appendFileSync(logFile, logLine);
}

// Create transporter
function createTransporter() {
  const smtpHost = process.env.SMTP_HOST || 'smtp.gmail.com';
  const smtpPort = parseInt(process.env.SMTP_PORT || '587');
  const smtpUser = process.env.SMTP_USER || '';
  const smtpPass = process.env.SMTP_PASS || '';
  const smtpSecure = process.env.SMTP_SECURE === 'true';
  
  if (!smtpUser || !smtpPass) {
    log('WARN', 'SMTP credentials not configured, email sending will fail');
  }
  
  return nodemailer.createTransport({
    host: smtpHost,
    port: smtpPort,
    secure: smtpSecure,
    auth: smtpUser && smtpPass ? {
      user: smtpUser,
      pass: smtpPass,
    } : undefined,
  });
}

// Validate email address
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Send email
async function sendEmail(options) {
  const { to, cc, bcc, subject, body, html, attachments } = options;
  
  // Validate recipients
  const recipients = [];
  if (to) {
    const toArr = Array.isArray(to) ? to : [to];
    for (const addr of toArr) {
      if (!isValidEmail(addr)) {
        throw new Error(`Invalid 'to' email address: ${addr}`);
      }
      recipients.push(addr);
    }
  }
  
  if (cc) {
    const ccArr = Array.isArray(cc) ? cc : [cc];
    for (const addr of ccArr) {
      if (!isValidEmail(addr)) {
        throw new Error(`Invalid 'cc' email address: ${addr}`);
      }
    }
  }
  
  if (bcc) {
    const bccArr = Array.isArray(bcc) ? bcc : [bcc];
    for (const addr of bccArr) {
      if (!isValidEmail(addr)) {
        throw new Error(`Invalid 'bcc' email address: ${addr}`);
      }
    }
  }
  
  if (recipients.length === 0) {
    throw new Error('At least one recipient is required');
  }
  
  if (!subject) {
    throw new Error('Email subject is required');
  }
  
  if (!body && !html) {
    throw new Error('Email body or HTML content is required');
  }
  
  // Create transporter and send
  const transporter = createTransporter();
  
  const mailOptions = {
    from: process.env.SMTP_FROM || process.env.SMTP_USER || 'ai-employee@localhost',
    to: recipients.join(', '),
    cc: cc ? (Array.isArray(cc) ? cc.join(', ') : cc) : undefined,
    bcc: bcc ? (Array.isArray(bcc) ? bcc.join(', ') : bcc) : undefined,
    subject: subject,
    text: body || undefined,
    html: html || undefined,
    attachments: attachments || [],
  };
  
  log('INFO', `Sending email to: ${recipients.join(', ')}, Subject: ${subject}`);
  
  try {
    const info = await transporter.sendMail(mailOptions);
    log('INFO', `Email sent successfully: ${info.messageId}`);
    
    // Log to vault
    const logEntry = {
      timestamp: new Date().toISOString(),
      action: 'email_sent',
      messageId: info.messageId,
      to: recipients,
      subject: subject,
      status: 'success',
    };
    
    const logFile = join(DONE_DIR, `email_${Date.now()}.json`);
    fs.writeFileSync(logFile, JSON.stringify(logEntry, null, 2));
    
    return {
      success: true,
      messageId: info.messageId,
      message: 'Email sent successfully',
    };
  } catch (error) {
    log('ERROR', `Failed to send email: ${error.message}`);
    
    // Log error
    const errorEntry = {
      timestamp: new Date().toISOString(),
      action: 'email_failed',
      to: recipients,
      subject: subject,
      error: error.message,
      status: 'error',
    };
    
    const errorFile = join(LOGS_DIR, `email_error_${Date.now()}.json`);
    fs.writeFileSync(errorFile, JSON.stringify(errorEntry, null, 2));
    
    throw error;
  }
}

// Create MCP Server
const server = new Server(
  {
    name: 'email-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'send_email',
        description: 'Send an email message. Requires SMTP configuration via environment variables.',
        inputSchema: {
          type: 'object',
          properties: {
            to: {
              type: 'array',
              items: { type: 'string' },
              description: 'Recipient email addresses (required)',
            },
            cc: {
              type: 'array',
              items: { type: 'string' },
              description: 'CC email addresses (optional)',
            },
            bcc: {
              type: 'array',
              items: { type: 'string' },
              description: 'BCC email addresses (optional)',
            },
            subject: {
              type: 'string',
              description: 'Email subject (required)',
            },
            body: {
              type: 'string',
              description: 'Plain text email body (required if html not provided)',
            },
            html: {
              type: 'string',
              description: 'HTML email body (required if body not provided)',
            },
            attachments: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  filename: { type: 'string' },
                  content: { type: 'string' },
                  contentType: { type: 'string' },
                },
              },
              description: 'Email attachments (optional)',
            },
          },
          required: ['to', 'subject'],
        },
      },
      {
        name: 'test_connection',
        description: 'Test the SMTP connection to verify email configuration',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  log('INFO', `Tool called: ${name}`);
  
  try {
    switch (name) {
      case 'send_email': {
        if (!args) {
          throw new Error('No arguments provided');
        }
        
        const result = await sendEmail({
          to: args.to,
          cc: args.cc,
          bcc: args.bcc,
          subject: args.subject,
          body: args.body,
          html: args.html,
          attachments: args.attachments,
        });
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }
      
      case 'test_connection': {
        log('INFO', 'Testing SMTP connection...');
        
        try {
          const transporter = createTransporter();
          await transporter.verify();
          
          const result = {
            success: true,
            message: 'SMTP connection successful',
            host: process.env.SMTP_HOST || 'not configured',
          };
          
          log('INFO', 'SMTP connection test passed');
          
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        } catch (error) {
          const result = {
            success: false,
            message: `SMTP connection failed: ${error.message}`,
          };
          
          log('ERROR', result.message);
          
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }
      }
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    log('ERROR', `Tool execution error: ${error.message}`);
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(
            {
              success: false,
              error: error.message,
            },
            null,
            2
          ),
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  log('INFO', 'Starting Email MCP Server...');
  
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    log('INFO', 'Email MCP Server running on stdio');
  } catch (error) {
    log('ERROR', `Failed to start server: ${error.message}`);
    process.exit(1);
  }
}

main().catch((error) => {
  log('ERROR', `Fatal error: ${error.message}`);
  process.exit(1);
});
