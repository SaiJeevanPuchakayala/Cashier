from flask import Flask, render_template,request,redirect,url_for,session
from flask_mysqldb import MySQL
from messageService import send_sms
import os
import re

app = Flask(__name__)


db_name = os.environ.get("DB_NAME")
db_password = os.environ.get("DB_PASSWORD")
email = os.environ.get("ADMIN_MAIL_ID")
password = os.environ.get("ADMIN_MAIL_PASSWORD")


app.config['MYSQL_HOST'] = "remotemysql.com"
app.config['MYSQL_USER'] = db_name
app.config['MYSQL_PASSWORD'] = db_password
app.config['MYSQL_DB'] = db_name
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = email
app.config['MAIL_PASSWORD'] = password
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

mysql = MySQL(app)
app.secret_key = 'ecashier' 







@app.route('/')
def home():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date  FROM Purchases WHERE user_id = % s",[session['user_id']])
            purchase_details = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM Purchases WHERE user_id = %s",[session['user_id']])
            purchase_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Payments WHERE purchase_id IN (SELECT purchase_id FROM Purchases WHERE user_id = % s)",[session['user_id']])
            payment_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Purchases WHERE amount_paid<price AND user_id = % s",[session['user_id']])
            pending_count = cursor.fetchone()[0]
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchases")
            purchase_details = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM Purchases")
            purchase_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Payments")
            payment_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Purchases WHERE amount_paid<price")
            pending_count = cursor.fetchone()[0]
            
        return render_template('home.html',purchase_details=purchase_details,username=session['username'],role=session['is_retailer'],purchase_count=purchase_count,payment_count=payment_count,pending_count=pending_count)
    
    else:
        return redirect(url_for('intro'))
    


@app.route('/register', methods=['POST','GET'])
def register():
    success_message = None
    failed_message = None
    if 'loggedin' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        pnumber = request.form['pnumber']
        password1 = request.form['password1']
        password2 = request.form['password2']
        userWallet = request.form['walletAmount']

        if len(pnumber) == 10:
            if password1 == password2:
                if int(userWallet) >= 10000:
                    

                    cursor = mysql.connection.cursor()
                    cursor.execute('SELECT * FROM Users WHERE email = % s', [email])
                    account = cursor.fetchone()
                    if account:
                        failed_message="Account already exists...Try with different email address"
                    elif not re.match(r'[A-Za-z0-9]+', username):
                        failed_message = 'Username must contain only characters and numbers.'
                    else:
                        cursor = mysql.connection.cursor()

                        cursor.execute('INSERT INTO Users(userid,username,email,phonenumber,password,wallet) VALUES(UUID(),% s,% s,% s,% s,% s)',(username,email,pnumber,password1,userWallet))
                        mysql.connection.commit()

                        cursor.execute('SELECT userid FROM Users WHERE username=%s', [username])
                        user_id = cursor.fetchone()

                        msg = f'''E-Cashier! Hello {username}, Verify your mobile number by clicking on the link below https://e-cashier.herokuapp.com/verify/{user_id[0]}'''

                        print(msg)
                        
                        send_sms(pnumber,msg)
                        success_message = "A verification link has been sent to Your Phone Number."

                else:
                    failed_message = "Wallet Amount Should be Minimum of 10000 Rupees."
            else:
                failed_message = "Passwords Do Not Match!"
        else:
            failed_message = "Your mobile number should contain 10 digits!"
        
    return render_template('register.html',failed_message=failed_message,success_message=success_message)

@app.route('/login',methods=['POST','GET'])
def login():
    message=None
    if 'loggedin' in session:
        return redirect(url_for('home'))
    if request.method =='POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM Users WHERE email = % s',[email])
        user = cursor.fetchone()
        
        if user and (user[4] == password):
            if user[7] == 1:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['is_retailer'] = user[5]
                session['email'] = user[2]
                session['loggedin'] = True
                return redirect(url_for('home'))
            else:
                cursor = mysql.connection.cursor()

                cursor.execute('SELECT * FROM Users WHERE email=%s', [email])
                user = cursor.fetchone()
                

                msg = f'''E-Cashier! Hello {user[1]}, Verify your mobile number by clicking on the link below https://e-cashier.herokuapp.com/verify/{user[0]}'''
                
                send_sms(user[3],msg)
                return render_template('verification.html')

        else:
            message="Log in Unsuccessful. Please check username and password"
        
    
    return render_template("login.html",message=message)



@app.route('/logout',methods=['POST','GET'])
def logout():
    session.pop('loggedin', None) 
    session.pop('user_id',None)
    session.pop('username',None)
    session.pop('is_retailer',None)
    session.pop('email',None)
    return redirect(url_for('intro'))
    
  
@app.route('/addpurchase',methods=['POST','GET'])
def addpurchase():
    message = None
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            if request.method == 'POST':
                customer = request.form['customer']
                item = request.form['item']
                price = request.form['price']
                purchase_date = request.form['purchase_date']
                amount_paid = request.form['amount_paid']
                if int(amount_paid) > int(price):
                    message = "Amount paid should be less than or equal to the actual price."
                
                else:
                    pending_amount = int(price) - int(amount_paid)
                    cursor = mysql.connection.cursor()
                    cursor.execute("INSERT INTO Purchases (user_id,item_name,price,purchase_date,amount_paid) VALUES(% s,% s,% s,% s, % s)",[customer,item,price,purchase_date,amount_paid])
                    mysql.connection.commit()
                    if pending_amount!=0:
                        
                        cursor.execute("SELECT phonenumber, username FROM Users WHERE userid = %s",[customer])
                        user_details = cursor.fetchone()
                        recipient = user_details[0]
                        username = user_details[1]


                        msg= f'''Pending Payment Alert! Hey {username}, we hope you are doing well. Pending Payment Details :Item :{item}, Price: {price}, Purchases Date: {purchase_date}, Amount Paid: {amount_paid}, Pending Amount: {pending_amount}'''
                        
                        send_sms(recipient,msg)
                        message = "Purchase added successfully!"

            
        
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM Users WHERE is_admin = 0")
            customers = cursor.fetchall()
       
            return render_template('addpurchase.html',customers = customers, message=message)
        
        return redirect(url_for('home'))
    else:
        return redirect(url_for('intro'))


@app.route('/updatepurchase/<int:id>',methods=['POST', 'GET'])
def updatepurchase(id):
    message = None
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            
            
            if request.method == 'POST':
                
                item = request.form['item']
                price = request.form['price']
                purchase_date = request.form['purchase_date']
                amount_paid = request.form['amount_paid']
                if int(amount_paid) > int(price):
                    message = "Amount paid should be less than or equal to the actual price."
                
                else:
                    cursor = mysql.connection.cursor()
                    cursor.execute("UPDATE Purchases SET item_name = %s, price = %s, amount_paid = %s, purchase_date = %s WHERE purchase_id = %s ",[item,price,amount_paid,purchase_date,id])
                    mysql.connection.commit()
                    message = "Purchase Updated Successfully!"
            
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM Purchases WHERE purchase_id = %s",[id])
            purchase = cursor.fetchone()
            
            
            return render_template('updatepurchase.html',purchase=purchase,message=message)
    else:
        return redirect(url_for('intro'))
    

@app.route('/deletepurchase/<int:id>',methods=['POST','GET'])
def deletepurchase(id):
    if 'loggedin' in session:
        if session['is_retailer']==1:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM Purchases WHERE purchase_id = %s",[id])
            cursor.execute("DELETE FROM Payments WHERE purchase_id  = %s",[id])
            mysql.connection.commit()
            return redirect(url_for('home'))
    else:
        return redirect(url_for('intro'))
    


@app.route('/addpayment',methods=['POST','GET'])
def addpayment():
    message = None
    if 'loggedin' in session:
        if session['is_retailer']==1:
            if request.method == 'POST':
                purchase_id = request.form['purchase_id']
                amountpaid = request.form['amount_paid']
                payment_date = request.form['payment_date']
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT price, amount_paid FROM Purchases WHERE purchase_id = %s",[purchase_id])
                amount_paid = cursor.fetchone()
                if int(amountpaid) > int(amount_paid[0]-amount_paid[1]):
                    message = "Amount paid is more than the Actual Amount to be Paid."
                else:
                    cursor.execute("INSERT INTO Payments(purchase_id, amount_paid, payment_date) VALUES(% s,% s,% s)",[purchase_id,amountpaid,payment_date])
                    cursor.execute("UPDATE Purchases SET amount_paid=amount_paid + % s WHERE purchase_id = % s",[amountpaid,purchase_id])
                    mysql.connection.commit()
                    cursor.execute("SELECT item_name, price, amount_paid, user_id, purchase_date FROM Purchases WHERE purchase_id = %s",[purchase_id])
                    details = cursor.fetchone()
                    item = details[0]
                    price = details[1]
                    tot_amount_paid = details[2]
                    userid = details[3]
                    purchase_date = details[4]
                    cursor.execute("SELECT phonenumber, username FROM Users WHERE userid = %s",[userid])
                    user = cursor.fetchone()
                    recipient = user[0]
                    username = user[1]
                    pending_amount = price-tot_amount_paid

                    message = "Payment added successfully!"

                    msg = f'''Payment Detail! Hey {username}, we hope you are doing well. Payment Details: Item : {item}, Amount Paid: {amountpaid}, Payment Date: {payment_date} / Pending Payment Details : Item : {item}, Price: {price}, Purchases Date: {purchase_date}, Amount Paid: {tot_amount_paid}, Pending Amount: {pending_amount}'''
                   
                    send_sms(recipient,msg)


        return render_template('addpayment.html',message=message)
    else:
        return redirect(url_for('intro'))
    
@app.route('/pendingpayments')
def pendingpayments():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchases WHERE amount_paid<price AND user_id = % s",[session['user_id']])
            pending_payments = cursor.fetchall()
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchases WHERE amount_paid<price")
            pending_payments = cursor.fetchall()
        
        
        return render_template('pending_payments.html',pending_payments=pending_payments,username=session['username'],role=session['is_retailer'])
    else:
        return redirect(url_for('intro'))

@app.route('/paymentdetails')
def paymentdetails():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
         cursor = mysql.connection.cursor()
         cursor.execute("SELECT * FROM Payments WHERE purchase_id IN (SELECT purchase_id FROM Purchases WHERE user_id = % s)",[session['user_id']])
         payment_details = cursor.fetchall()
        else:
          cursor = mysql.connection.cursor()
          cursor.execute("SELECT * FROM Payments")
          payment_details = cursor.fetchall() 
        
        return render_template('paymentdetails.html',payments=payment_details,username=session['username'])
    else:
        return redirect(url_for('intro'))

@app.route('/contact')
def contact():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            return render_template('contact.html',username=session['username'])
    return redirect(url_for('intro'))

@app.route('/pendingalert/<int:id>')
def pendingalert(id):
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT phonenumber, username FROM Users WHERE user_id = %s",[id])
            details = cursor.fetchone()
            recipient = details[0]
            recipient_name = details[1]
            cursor.execute("select item_name, price, purchase_date, amount_paid FROM Purchases WHERE user_id = %s",[id])
            purchase = cursor.fetchone()
            pending_amount = int(purchase[1]) - int(purchase[3])

            msg = f'''Pending Payment Alert!!! Hey {recipient_name}, we hope you are doing well. The payment is still pending for the purchase item - {purchase[0]} made on {purchase[2]}. Pay the pending payment within two days without fail. Pending Payment Details :Item: {purchase[0]}, Price: {purchase[1]}, Purchases Date: {purchase[2]}, Amount Paid: {purchase[3]}, Pending Amount: {pending_amount}'''
            
            send_sms(recipient,msg)
        return redirect(url_for('pendingpayments'))
    else:
        redirect(url_for('intro'))


@app.route('/verify/<string:id>')
def verify(id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE Users SET is_verified = 1 WHERE userid = % s",[id])
    mysql.connection.commit()
    return redirect(url_for('login'))    
        
@app.route('/intro')
def intro():
    if 'loggedin' in session:
        return redirect(url_for('home'))
    return render_template('intro.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.errorhandler(404)
def page_not_found(e):
    if 'loggedin' in session:
        return redirect(url_for('home'))
    return render_template('intro.html')


if __name__ == '__main__':
    app.run(debug=True,port="8080")
