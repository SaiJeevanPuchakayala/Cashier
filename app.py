from flask import Flask, render_template,request,redirect,url_for,session
from flask_mysqldb import MySQL
from messageService import send_sms
import os
from flask_bcrypt import Bcrypt
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


bcrypt = Bcrypt(app)





@app.route('/')
def home():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date  FROM Purchase WHERE user_id = % s",[session['user_id']])
            purchase_details = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM Purchase WHERE user_id = %s",[session['user_id']])
            purchase_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Payments WHERE purchase_id IN (SELECT purchase_id FROM Purchase WHERE user_id = % s)",[session['user_id']])
            payment_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Purchase WHERE amount_paid<price AND user_id = % s",[session['user_id']])
            pending_count = cursor.fetchone()[0]
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchase")
            purchase_details = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM Purchase")
            purchase_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Payments")
            payment_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Purchase WHERE amount_paid<price")
            pending_count = cursor.fetchone()[0]
            
        return render_template('home.html',purchase_details=purchase_details,username=session['username'],role=session['is_retailer'],purchase_count=purchase_count,payment_count=payment_count,pending_count=pending_count)
    
    else:
        return redirect(url_for('intro'))
    


@app.route('/register', methods=['POST','GET'])
def register():
    message=None
    if 'loggedin' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        pnumber = request.form['pnumber']
        password1 = request.form['password1']
        password2 = request.form['password2']
        userWallet = request.form['walletAmount']
        if password1 == password2:

            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM Users WHERE email = % s', [email])
            account = cursor.fetchone()
            if account:
                message="Account already exists...Try with different email address"
            elif not re.match(r'[A-Za-z0-9]+', username):
                message = 'Username must contain only characters and numbers.'
            else:
                hash_password = bcrypt.generate_password_hash(password1).decode('utf-8')
                cursor = mysql.connection.cursor()
                cursor.execute('INSERT INTO Users(username,email,phonenumber,password,wallet) VALUES(% s,% s,% s,% s,% s)',(username,email,pnumber,hash_password,userWallet))
                mysql.connection.commit()


                msg = f'''Registration Successful! Hello {username}, Welcome to E Cashier!. Login to your account and see your purchase history, payment details, and pending payments.'''
                
                send_sms(pnumber,msg)
                return redirect(url_for('login'))
        
        else:
            message = "Passwords Do Not Match!"
        
    return render_template('register.html',message=message)

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
        
        if user and bcrypt.check_password_hash(user[3],password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_retailer'] = user[4]
            session['email'] = user[2]
            session['loggedin'] = True
            return redirect(url_for('home'))
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
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            if request.method == 'POST':
                customer = request.form['customer']
                item = request.form['item']
                price = request.form['price']
                purchase_date = request.form['purchase_date']
                amount_paid = request.form['amount_paid']
                pending_amount = int(price) - int(amount_paid)
                cursor = mysql.connection.cursor()
                cursor.execute("INSERT INTO Purchase(user_id,item_name,price,purchase_date,amount_paid) VALUES(% s,% s,% s,% s, % s)",[customer,item,price,purchase_date,amount_paid])
                mysql.connection.commit()
                if pending_amount!=0:
                    
                    cursor.execute("SELECT phonenumber, username FROM Users WHERE user_id = %s",[customer])
                    user_details = cursor.fetchone()
                    recipient = user_details[0]
                    username = user_details[1]


                    msg= f'''Pending Payment Alert! Hey {username}, we hope you are doing well. Pending Payment Details :Item :{item}, Price: {price}, Purchase Date: {purchase_date}, Amount Paid: {amount_paid}, Pending Amount: {pending_amount}'''
                    
                    send_sms(recipient,msg)


                return redirect(url_for('home'))
            
        
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM Users WHERE is_admin = 0")
            customers = cursor.fetchall()
       
            return render_template('addpurchase.html',customers = customers)
        
        return redirect(url_for('home'))
    else:
        return redirect(url_for('intro'))


@app.route('/updatepurchase/<int:id>',methods=['POST', 'GET'])
def updatepurchase(id):
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            
            
            if request.method == 'POST':
                
                item = request.form['item']
                price = request.form['price']
                purchase_date = request.form['purchase_date']
                amount_paid = request.form['amount_paid']
                cursor = mysql.connection.cursor()
                cursor.execute("UPDATE Purchase SET item_name = %s, price = %s, amount_paid = %s, purchase_date = %s WHERE purchase_id = %s ",[item,price,amount_paid,purchase_date,id])
                mysql.connection.commit()
                return redirect(url_for('home'))
            
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM Purchase WHERE purchase_id = %s",[id])
            purchase = cursor.fetchone()
            
            
            return render_template('updatepurchase.html',purchase=purchase)
    else:
        return redirect(url_for('intro'))
    

@app.route('/deletepurchase/<int:id>',methods=['POST','GET'])
def deletepurchase(id):
    if 'loggedin' in session:
        if session['is_retailer']==1:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM Purchase WHERE purchase_id = %s",[id])
            cursor.execute("DELETE FROM Payments WHERE purchase_id  = %s",[id])
            mysql.connection.commit()
            return redirect(url_for('home'))
    else:
        return redirect(url_for('intro'))
    


@app.route('/displaypurchase')
def displaypurchase():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date  FROM Purchase WHERE user_id = % s",[session['user_id']])
            purchase_details = cursor.fetchall()
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchase")
            purchase_details = cursor.fetchall()
    
   
        return render_template('displaypurchase.html',purchase_details=purchase_details,username=session['username'])
    
    else:
        return redirect(url_for('intro'))
    


@app.route('/addpayment',methods=['POST','GET'])
def addpayment():
    if 'loggedin' in session:
        if session['is_retailer']==1:
            if request.method == 'POST':
                purchase_id = request.form['purchase_id']
                amountpaid = request.form['amount_paid']
                payment_date = request.form['payment_date']
                cursor = mysql.connection.cursor()
                cursor.execute("INSERT INTO Payments(purchase_id, amount_paid, payment_date) VALUES(% s,% s,% s)",[purchase_id,amountpaid,payment_date])
                cursor.execute("UPDATE Purchase SET amount_paid=amount_paid + % s WHERE purchase_id = % s",[amountpaid,purchase_id])
                mysql.connection.commit()
                cursor.execute("SELECT item_name, price, amount_paid, user_id, purchase_date FROM Purchase WHERE purchase_id = %s",[purchase_id])
                details = cursor.fetchone()
                item = details[0]
                price = details[1]
                tot_amount_paid = details[2]
                userid = details[3]
                purchase_date = details[4]
                cursor.execute("SELECT phonenumber, username FROM Users WHERE user_id = %s",[userid])
                user = cursor.fetchone()
                recipient = user[0]
                username = user[1]
                pending_amount = price-tot_amount_paid


                msg = f'''Payment Detail! Hey {username}, we hope you are doing well. Payment Details: Item : {item}, Amount Paid: {amountpaid}, Payment Date: {payment_date} / Pending Payment Details : Item : {item}, Price: {price}, Purchase Date: {purchase_date}, Amount Paid: {tot_amount_paid}, Pending Amount: {pending_amount}'''
                   
                send_sms(recipient,msg)
                return redirect(url_for('home'))
        return render_template('addpayment.html')
    else:
        return redirect(url_for('intro'))
    
@app.route('/pendingpayments')
def pendingpayments():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchase WHERE amount_paid<price AND user_id = % s",[session['user_id']])
            pending_payments = cursor.fetchall()
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT purchase_id,user_id,item_name, price, amount_paid, purchase_date FROM Purchase WHERE amount_paid<price")
            pending_payments = cursor.fetchall()
        
        
        return render_template('pending_payments.html',pending_payments=pending_payments,username=session['username'],role=session['is_retailer'])
    else:
        return redirect(url_for('intro'))

@app.route('/paymentdetails/')
def paymentdetails():
    if 'loggedin' in session:
        if session['is_retailer'] == 0:
         cursor = mysql.connection.cursor()
         cursor.execute("SELECT * FROM Payments WHERE purchase_id IN (SELECT purchase_id FROM Purchase WHERE user_id = % s)",[session['user_id']])
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

@app.route('/pendingemail/<int:id>')
def pendingemail(id):
    if 'loggedin' in session:
        if session['is_retailer'] == 1:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT phonenumber, username FROM Users WHERE user_id = %s",[id])
            details = cursor.fetchone()
            recipient = details[0]
            recipient_name = details[1]
            cursor.execute("Select item_name, price, purchase_date, amount_paid FROM Purchase WHERE user_id = %s",[id])
            purchase = cursor.fetchone()
            pending_amount = int(purchase[1]) - int(purchase[3])

            msg = f'''Pending Payment Alert!!! Hey {recipient_name}, we hope you are doing well. The payment is still pending for the purchase item - {purchase[0]} made on {purchase[2]}. Pay the pending payment within two days without fail. Pending Payment Details :Item: {purchase[0]}, Price: {purchase[1]}, Purchase Date: {purchase[2]}, Amount Paid: {purchase[3]}, Pending Amount: {pending_amount}'''
            
            send_sms(recipient,msg)
        return redirect(url_for('pendingpayments'))
    else:
        redirect(url_for('intro'))
        
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
