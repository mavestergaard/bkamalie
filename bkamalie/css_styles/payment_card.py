from bkamalie.app.model import DisplayPayment

def get_payment_card_style()-> str:
    return """
<style>
    .card-container {
        display: flex;
        flex-direction: column;
        width: 100%;
    }
    .payment-card {
        width: 100%;
        padding: 10px 15px;
        margin-bottom: 5px;
        background: #f9f9f9;
        border-left: 6px solid #28A745; /* Default green for accepted */
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 14px;
    }
    .payment-card.pending {
        border-left-color: orange;
    }
    .payment-card.declined {
        border-left-color: red;
    }
    .payment-left {
        flex: 2;
        text-align: left;
    }
    .payment-middle {
        flex: 2;
        text-align: center;
        color: #555;
    }
    .payment-right {
        flex: 1;
        text-align: right;
        color: #555;
    }
    .payment-status {
        font-weight: bold;
    }
    .payment-name {
        font-weight: bold;
        display: block;
    }
    .payment-amount {
        font-weight: bold;
        color: #000;
    }
</style>
"""

def get_payment_card_html(payment: DisplayPayment) -> str:
    status_class = payment.payment_status.lower()
    return f"""
    <div class="payment-card {status_class}">
        <div class="payment-left">
            <div class="payment-name">{payment.member_name}</div>
            <div>{payment.payment_date.strftime('%d %b %Y')}</div>
        </div>
        <div class="payment-middle">
            <div class="payment-status">{payment.payment_status}</div>
        </div>
        <div class="payment-right">
            <div class="payment-amount">{payment.amount} DKK</div>
        </div>
    </div>
    """