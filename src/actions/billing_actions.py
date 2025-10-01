# ==================== src/actions/billing_actions.py ====================
"""
Billing domain actions for BillingAgentL3.
Handles invoices, payments, account inquiries.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from bson import ObjectId

from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class BillingActions:
    """Actions for billing/payment domain."""
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize billing actions.
        
        Args:
            db_service: Database service for data operations
        """
        self.db_service = db_service
    
    async def get_account_balance(
        self,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Get the current account balance for a client.
        
        Args:
            client_id: Client ObjectId
        
        Returns:
            {
                "success": bool,
                "client_id": str,
                "balance": float,
                "outstanding_invoices": int,
                "last_payment_date": str
            }
        """
        try:
            logger.info(f"Getting account balance for client {client_id}")
            
            # Get client
            client = await self.db_service.find_client_by_id(ObjectId(client_id))
            
            if not client:
                return {
                    "success": False,
                    "error_code": "CLIENT_NOT_FOUND",
                    "error_message": f"Client {client_id} not found"
                }
            
            # Calculate balance from unpaid jobs (simple implementation)
            # In production, use a proper invoicing system
            unpaid_jobs = []
            cursor = self.db_service.db.jobs.find({
                "client_id": ObjectId(client_id),
                "status": "completed",
                "payment_status": {"$ne": "paid"}
            })
            
            total_balance = 0.0
            async for job in cursor:
                amount = job.get("amount", 0.0)
                total_balance += amount
                unpaid_jobs.append(str(job["_id"]))
            
            # Get last payment date (placeholder)
            last_payment = await self.db_service.db.payments.find_one(
                {"client_id": ObjectId(client_id)},
                sort=[("payment_date", -1)]
            )
            
            last_payment_date = last_payment.get("payment_date") if last_payment else None
            
            logger.info(f"Account balance retrieved: ${total_balance}")
            
            return {
                "success": True,
                "client_id": client_id,
                "balance": total_balance,
                "outstanding_invoices": len(unpaid_jobs),
                "last_payment_date": last_payment_date.isoformat() if last_payment_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            return {
                "success": False,
                "error_code": "BALANCE_QUERY_FAILED",
                "error_message": str(e)
            }
    
    async def send_invoice(
        self,
        job_id: str,
        amount: float,
        due_date: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate and send an invoice for a job.
        
        Args:
            job_id: Job ObjectId
            amount: Invoice amount
            due_date: Payment due date (ISO format)
            items: Line items for the invoice
        
        Returns:
            {
                "success": bool,
                "invoice_id": str,
                "invoice_number": str,
                "amount": float,
                "due_date": str
            }
        """
        try:
            logger.info(f"Sending invoice for job {job_id}")
            
            # Get job details
            job = await self.db_service.db.jobs.find_one({"_id": ObjectId(job_id)})
            
            if not job:
                return {
                    "success": False,
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"Job {job_id} not found"
                }
            
            # Parse due date or set default (30 days)
            if due_date:
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                except ValueError:
                    due_datetime = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + 30)
            else:
                due_datetime = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + 30)
            
            # Generate invoice
            invoice_id = ObjectId()
            invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{str(invoice_id)[-6:].upper()}"
            
            invoice_doc = {
                "_id": invoice_id,
                "invoice_number": invoice_number,
                "job_id": ObjectId(job_id),
                "client_id": job.get("client_id"),
                "amount": amount,
                "status": "sent",
                "issued_date": datetime.now(timezone.utc),
                "due_date": due_datetime,
                "items": items or [],
                "paid_date": None,
                "payment_method": None
            }
            
            # Save invoice
            await self.db_service.db.invoices.insert_one(invoice_doc)
            
            # Update job payment status
            await self.db_service.db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "payment_status": "invoiced",
                        "invoice_id": invoice_id,
                        "amount": amount
                    }
                }
            )
            
            # Send invoice to client (placeholder)
            await self._send_invoice_email(invoice_number, job.get("client_id"), amount)
            
            logger.info(f"Invoice sent successfully: {invoice_number}")
            
            return {
                "success": True,
                "invoice_id": str(invoice_id),
                "invoice_number": invoice_number,
                "amount": amount,
                "due_date": due_datetime.isoformat(),
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Invoice generation failed: {e}")
            return {
                "success": False,
                "error_code": "INVOICE_FAILED",
                "error_message": str(e)
            }
    
    async def process_payment(
        self,
        invoice_id: str,
        amount: float,
        payment_method: str,
        confirmation_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a payment for an invoice.
        
        Args:
            invoice_id: Invoice ObjectId
            amount: Payment amount
            payment_method: Payment method (e.g., "card", "cash", "check")
            confirmation_number: External payment confirmation number
        
        Returns:
            {
                "success": bool,
                "payment_id": str,
                "receipt_number": str,
                "amount": float
            }
        """
        try:
            logger.info(f"Processing payment for invoice {invoice_id}")
            
            # Get invoice
            invoice = await self.db_service.db.invoices.find_one({"_id": ObjectId(invoice_id)})
            
            if not invoice:
                return {
                    "success": False,
                    "error_code": "INVOICE_NOT_FOUND",
                    "error_message": f"Invoice {invoice_id} not found"
                }
            
            # Check if already paid
            if invoice.get("status") == "paid":
                return {
                    "success": False,
                    "error_code": "ALREADY_PAID",
                    "error_message": "This invoice has already been paid"
                }
            
            # Validate amount
            invoice_amount = invoice.get("amount", 0.0)
            if amount < invoice_amount:
                return {
                    "success": False,
                    "error_code": "INSUFFICIENT_PAYMENT",
                    "error_message": f"Payment amount ${amount} is less than invoice amount ${invoice_amount}"
                }
            
            # Create payment record
            payment_id = ObjectId()
            receipt_number = f"RCP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(payment_id)[-6:].upper()}"
            
            payment_doc = {
                "_id": payment_id,
                "receipt_number": receipt_number,
                "invoice_id": ObjectId(invoice_id),
                "client_id": invoice.get("client_id"),
                "amount": amount,
                "payment_method": payment_method,
                "payment_date": datetime.now(timezone.utc),
                "confirmation_number": confirmation_number,
                "status": "completed"
            }
            
            # Save payment
            await self.db_service.db.payments.insert_one(payment_doc)
            
            # Update invoice
            await self.db_service.db.invoices.update_one(
                {"_id": ObjectId(invoice_id)},
                {
                    "$set": {
                        "status": "paid",
                        "paid_date": datetime.now(timezone.utc),
                        "payment_method": payment_method,
                        "payment_id": payment_id
                    }
                }
            )
            
            # Update job
            await self.db_service.db.jobs.update_one(
                {"invoice_id": ObjectId(invoice_id)},
                {"$set": {"payment_status": "paid"}}
            )
            
            # Send receipt (placeholder)
            await self._send_receipt(receipt_number, invoice.get("client_id"), amount)
            
            logger.info(f"Payment processed successfully: {receipt_number}")
            
            return {
                "success": True,
                "payment_id": str(payment_id),
                "receipt_number": receipt_number,
                "amount": amount,
                "payment_date": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return {
                "success": False,
                "error_code": "PAYMENT_FAILED",
                "error_message": str(e)
            }
    
    async def request_payment_plan(
        self,
        client_id: str,
        total_amount: float,
        num_installments: int
    ) -> Dict[str, Any]:
        """
        Set up a payment plan for a client.
        
        Args:
            client_id: Client ObjectId
            total_amount: Total amount to be paid
            num_installments: Number of installments
        
        Returns:
            {
                "success": bool,
                "plan_id": str,
                "installment_amount": float,
                "installments": List[Dict]
            }
        """
        try:
            logger.info(f"Creating payment plan for client {client_id}")
            
            # Validate
            if num_installments < 2 or num_installments > 12:
                return {
                    "success": False,
                    "error_code": "INVALID_INSTALLMENTS",
                    "error_message": "Number of installments must be between 2 and 12"
                }
            
            # Calculate installment amount
            installment_amount = round(total_amount / num_installments, 2)
            
            # Adjust last installment for rounding
            last_installment = total_amount - (installment_amount * (num_installments - 1))
            
            # Create installment schedule
            installments = []
            current_date = datetime.now(timezone.utc)
            
            for i in range(num_installments):
                due_date = current_date.replace(month=current_date.month + i + 1)
                amount = last_installment if i == num_installments - 1 else installment_amount
                
                installments.append({
                    "installment_number": i + 1,
                    "amount": amount,
                    "due_date": due_date.isoformat(),
                    "status": "pending"
                })
            
            # Create payment plan
            plan_id = ObjectId()
            plan_doc = {
                "_id": plan_id,
                "client_id": ObjectId(client_id),
                "total_amount": total_amount,
                "installment_amount": installment_amount,
                "num_installments": num_installments,
                "installments": installments,
                "status": "active",
                "created_at": datetime.now(timezone.utc)
            }
            
            # Save plan
            await self.db_service.db.payment_plans.insert_one(plan_doc)
            
            logger.info(f"Payment plan created: {plan_id}")
            
            return {
                "success": True,
                "plan_id": str(plan_id),
                "total_amount": total_amount,
                "installment_amount": installment_amount,
                "num_installments": num_installments,
                "installments": installments
            }
            
        except Exception as e:
            logger.error(f"Payment plan creation failed: {e}")
            return {
                "success": False,
                "error_code": "PLAN_CREATION_FAILED",
                "error_message": str(e)
            }
    
    # ============ Helper Methods ============
    
    async def _send_invoice_email(
        self,
        invoice_number: str,
        client_id: Optional[ObjectId],
        amount: float
    ):
        """Send invoice via email."""
        logger.info(f"Sending invoice {invoice_number} - ${amount}")
        # Placeholder - implement actual email service
    
    async def _send_receipt(
        self,
        receipt_number: str,
        client_id: Optional[ObjectId],
        amount: float
    ):
        """Send payment receipt."""
        logger.info(f"Sending receipt {receipt_number} - ${amount}")
        # Placeholder - implement actual email service