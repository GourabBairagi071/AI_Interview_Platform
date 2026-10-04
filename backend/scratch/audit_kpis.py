import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, func, and_, or_, text
from app.modules.auth.model import User, UserProfile
from app.modules.interview.model import Interview
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.coding.contest_model import Contest
from app.modules.practice.model import PracticeQuestion
from app.modules.payments.model import PaymentTransaction, UserSubscription, SubscriptionPlan
from app.modules.support.model import SupportTicket, Feedback
from app.modules.resume.model import Resume
from app.modules.learning.model import LearningProfile
from app.modules.rag.model import InterviewQuestionVector

async def audit():
    async with AsyncSessionLocal() as session:
        print("=== DATABASE TABLES & CURRENT METRICS ===")
        
        # 1. Users
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (await session.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
        print(f"Total Users: {total_users}, Active Users: {active_users}")
        
        # 2. Interviews
        total_interviews = (await session.execute(select(func.count(Interview.id)))).scalar() or 0
        completed_interviews = (await session.execute(select(func.count(Interview.id)).where(Interview.status == 'completed'))).scalar() or 0
        
        avg_score_raw = (await session.execute(select(func.avg(Interview.score)).where(and_(Interview.status == 'completed', Interview.score.isnot(None))))).scalar()
        avg_score = round(float(avg_score_raw), 2) if avg_score_raw is not None else 0.0
        print(f"Total Interviews: {total_interviews}, Completed: {completed_interviews}, Avg Score: {avg_score}")

        # Check interview statuses distribution
        int_statuses = (await session.execute(select(Interview.status, func.count(Interview.id)).group_by(Interview.status))).all()
        print("Interview Statuses:", int_statuses)

        # 3. Resumes & ATS
        resumes_count = (await session.execute(select(func.count(Resume.id)))).scalar() or 0
        print(f"Total Resumes: {resumes_count}")

        # Check columns of resumes
        col_res = await session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'resumes'"))
        print("Resumes table columns:", col_res.fetchall())

        # 4. Subscriptions
        total_plans = (await session.execute(select(func.count(SubscriptionPlan.id)))).scalar() or 0
        active_subs = (await session.execute(select(func.count(UserSubscription.id)).where(UserSubscription.status == 'active'))).scalar() or 0
        all_subs = (await session.execute(select(func.count(UserSubscription.id)))).scalar() or 0
        sub_statuses = (await session.execute(select(UserSubscription.status, func.count(UserSubscription.id)).group_by(UserSubscription.status))).all()
        print(f"Total Subscription Plans: {total_plans}, Active User Subscriptions: {active_subs}, All User Subs: {all_subs}")
        print("User Subscription Statuses:", sub_statuses)

        # 5. Payments
        total_payments = (await session.execute(select(func.count(PaymentTransaction.id)))).scalar() or 0
        pay_statuses = (await session.execute(select(PaymentTransaction.status, func.count(PaymentTransaction.id), func.sum(PaymentTransaction.amount)).group_by(PaymentTransaction.status))).all()
        print(f"Total Payment Transactions: {total_payments}")
        print("Payment Statuses & Amounts (paise):", pay_statuses)

        # 6. Support Tickets
        total_tickets = (await session.execute(select(func.count(SupportTicket.id)))).scalar() or 0
        ticket_statuses = (await session.execute(select(SupportTicket.status, func.count(SupportTicket.id)).group_by(SupportTicket.status))).all()
        pending_tickets = (await session.execute(select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(['open', 'in_progress', 'waiting_user'])))).scalar() or 0
        print(f"Total Tickets: {total_tickets}, Pending (open/in_prog/waiting): {pending_tickets}")
        print("Ticket Statuses:", ticket_statuses)

        # 7. Questions & Problems
        questions_count = (await session.execute(select(func.count(PracticeQuestion.id)))).scalar() or 0
        problems_count = (await session.execute(select(func.count(CodingProblem.id)))).scalar() or 0
        submissions_count = (await session.execute(select(func.count(CodingSubmission.id)))).scalar() or 0
        contests_count = (await session.execute(select(func.count(Contest.id)))).scalar() or 0
        vectors_count = (await session.execute(select(func.count(InterviewQuestionVector.id)))).scalar() or 0
        print(f"Practice Questions: {questions_count}")
        print(f"Coding Problems: {problems_count}, Submissions: {submissions_count}")
        print(f"Contests: {contests_count}")
        print(f"RAG Vectors: {vectors_count}")

if __name__ == '__main__':
    asyncio.run(audit())
