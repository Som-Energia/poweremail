#########################################################################
#Power Email is a module for Open ERP which enables it to send mails    #
#Core settings are stored here                                          #
#########################################################################
#   #####     #   #        # ####  ###     ###  #   #   ##  ###   #     #
#   #   #   #  #   #      #  #     #  #    #    # # #  #  #  #    #     #
#   ####    #   #   #    #   ###   ###     ###  #   #  #  #  #    #     #
#   #        # #    # # #    #     # #     #    #   #  ####  #    #     #
#   #         #     #  #     ####  #  #    ###  #   #  #  # ###   ####  #
# Copyright (C) 2009  Sharoon Thomas                                    #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
# any later version.                                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
from osv import osv, fields
import netsvc
import re

class poweremail_templates(osv.osv):
    _name="poweremail.templates"
    _description = 'Power Email Templates for Models'

    _columns = {
        'name' : fields.char('Name of Template',size=100,required=True),
        'object_name':fields.many2one('ir.model','Model'),
        'def_to':fields.char('Recepient (To)',size=64,help="The default recepient of email. Placeholders can be used here."),
        'def_cc':fields.char('Default CC',size=64,help="The default CC for the email. Placeholders can be used here."),
        'def_bcc':fields.char('Default BCC',size=64,help="The default BCC for the email. Placeholders can be used here."),
        'def_subject':fields.char('Default Subject',size=200, help="The default subject of email. Placeholders can be used here."),
        'def_body':fields.text('Standard Body',help="The Signatures will be automatically appended"),
        'use_sign':fields.boolean('Use Signature',help="the signature from the User details will be appened to the mail"),
        'file_name':fields.char('File Name Pattern',size=200,help="File name pattern can be specified with placeholders. eg. 2009_SO003.pdf"),
        'allowed_groups':fields.many2many('res.groups','template_group_rel','templ_id','group_id',string="Allowed User Groups",  help="Only users from these groups will be allowed to send mails from this ID"),
        'enforce_from_account':fields.many2one('poweremail.core_accounts',string="Enforce From Account",help="Emails will be sent only from this account.",domain="[('company','=','yes')]"),

        'auto_email':fields.boolean('Auto Email', help="Selecting Auto Email will create a server action for you which automatically sends mail after a new record is created."),
        'attached_wkf':fields.many2one('workflow','Workflow'),
        'attached_activity':fields.many2one('workflow.activity','Activity'),
        'server_action':fields.many2one('ir.actions.server','Related Server Action',help="Corresponding server action is here."),
        'model_object_field':fields.many2one('ir.model.fields',string="Field",help="Select the field from the model you want to use.\nIf it is a relationship field you will be able to choose the nested values in the box below\n(Note:If there are no values make sure you have selected the correct model)"),
        'sub_object':fields.many2one('ir.model','Sub-model',help='When a relation field is used this field will show you the type of field you have selected'),
        'sub_model_object_field':fields.many2one('ir.model.fields','Sub Field',help='When you choose relationship fields this field will specify the sub value you can use.'),
        'null_value':fields.char('Null Value',help="This Value is used if the field is empty",size=50),
        'copyvalue':fields.char('Expression',size=100,help="Copy and paste the value in the location you want to use a system value.")
    }

    _defaults = {

    }
    
    def _field_changed(self,cr,uid,ids,parent_field):
        #print "Parent:",parent_field
        if parent_field:
            field_obj = self.pool.get('ir.model.fields').browse(cr,uid,parent_field)
            #print field_obj.ttype
            if field_obj.ttype in ['many2one','one2many','many2many']:
                res_ids=self.pool.get('ir.model').search(cr,uid,[('model','=',field_obj.relation)])
                #print res_ids[0]
                if res_ids:
                    self.write(cr,uid,ids,{'model_object_field':parent_field,'sub_object':res_ids[0],'sub_model_object_field':False})
                    expr_val = self._add_field(cr,uid,ids)
                    return {'value':{'sub_object':res_ids[0],'copyvalue':expr_val['value']['copyvalue']}}
                else:
                    self.write(cr,uid,ids,{'model_object_field':parent_field,'sub_object':False,'sub_model_object_field':False})
                    expr_val = self._add_field(cr,uid,ids)
                    return {'value':{'sub_object':False,'sub_model_object_field':False,'copyvalue':expr_val['value']['copyvalue']}}
            else:
                self.write(cr,uid,ids,{'model_object_field':parent_field,'sub_object':False,'sub_model_object_field':False,})
                expr_val = self._add_field(cr,uid,ids)
                return {'value':{'sub_object':False,'sub_model_object_field':False,'copyvalue':expr_val['value']['copyvalue']}}
        else:
            expr_val = self._add_field(cr,uid,ids)
            self.write(cr,uid,ids,{'sub_object':False,'sub_model_object_field':False})
            return {'value':{'sub_object':False,'sub_model_object_field':False,'copyvalue':expr_val['value']['copyvalue']}}
        
    def _add_field(self,cr,uid,ids,ctx={}):
        if self.read(cr,uid,ids,['model_object_field'])[0]['model_object_field']:
            #print "Computing Field"
            obj_id = self.read(cr,uid,ids,['model_object_field'])[0]['model_object_field'][0]
            obj_br = self.pool.get('ir.model.fields').browse(cr,uid,obj_id)
            obj_not = obj_br.name
            if self.read(cr,uid,ids,['sub_model_object_field'])[0]['sub_model_object_field']:
                obj_id = self.read(cr,uid,ids,['sub_model_object_field'])[0]['sub_model_object_field'][0]
                obj_br = self.pool.get('ir.model.fields').browse(cr,uid,obj_id)
                obj_not = obj_not + "." + obj_br.name
            if self.read(cr,uid,ids,['null_value'])[0]['null_value']:
                obj_not = obj_not + "/" + self.read(cr,uid,ids,['null_value'])[0]['null_value']
            obj_not = "[[object." + obj_not + "]]"
            #print "Object Value (_add_field):",obj_not
            self.write(cr,uid,ids,{'copyvalue':obj_not})
            return {'value':{'copyvalue':obj_not}}

    def _auto_compute(self,cr,uid,ids,model_object_field,sub_model_object_field,null_value,ctx={}):
        if model_object_field:
            obj_id = model_object_field
            obj_br = self.pool.get('ir.model.fields').browse(cr,uid,obj_id)
            obj_not = obj_br.name
            if sub_model_object_field:
                obj_br = self.pool.get('ir.model.fields').browse(cr,uid,sub_model_object_field)
                obj_not = obj_not + "." + obj_br.name
            if null_value:
                obj_not = obj_not + "/" + null_value
            obj_not = "[[object." + obj_not + "]]"
            #print "Object Value (_suto_compute):",obj_not
            #self.write(cr,uid,ids,{'copyvalue':obj_not})
            return {'value':{'copyvalue':obj_not}}

poweremail_templates()

class poweremail_preview(osv.osv_memory):
    _name = "poweremail.preview"
    _description = "Power Email Template Preview"
    
    def _get_model_recs(self,cr,uid,ctx={}):
        self.context = ctx
        if 'active_id' in ctx.keys():
            ref_obj_id = self.pool.get('poweremail.templates').read(cr,uid,ctx['active_id'],['object_name'])['object_name']
            ref_obj_name = self.pool.get('ir.model').read(cr,uid,ref_obj_id[0],['model'])['model']
            ref_obj_ids = self.pool.get(ref_obj_name).search(cr,uid,[])
            ref_obj_recs = self.pool.get(ref_obj_name).name_get(cr,uid,ref_obj_ids)
            #print ref_obj_recs
            return ref_obj_recs

    _columns = {
        'ref_template':fields.many2one('poweremail.templates','Template',readonly=True),
        'rel_model':fields.many2one('ir.model','Model',readonly=True),
        'rel_model_ref':fields.selection(_get_model_recs,'Referred Document'),
        'to':fields.char('To',size=100,readonly=True),
        'cc':fields.char('CC',size=100,readonly=True),
        'bcc':fields.char('BCC',size=100,readonly=True),
        'subject':fields.char('Subject',size=200,readonly=True),
        'body_text':fields.text('Body',readonly=True),
        'body_html':fields.text('Body',readonly=True),
        'report':fields.char('Report Name',size=100,readonly=True),
    }
    _defaults = {
        'ref_template': lambda self,cr,uid,ctx:ctx['active_id'],
        'rel_model': lambda self,cr,uid,ctx:self.pool.get('poweremail.templates').read(cr,uid,ctx['active_id'],['object_name'])['object_name']
    }

    def strip_html(self,text):
        def fixup(m):
            text = m.group(0)
            if text[:1] == "<":
                return "" # ignore tags
            if text[:2] == "&#":
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            elif text[:1] == "&":
                import htmlentitydefs
                entity = htmlentitydefs.entitydefs.get(text[1:-1])
                if entity:
                    if entity[:2] == "&#":
                        try:
                            return unichr(int(entity[2:-1]))
                        except ValueError:
                            pass
                    else:
                        return unicode(entity, "iso-8859-1")
            return text # leave as is
        return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)

    def parsevalue(self,cr,uid,id,message,template,context):
        #id: ID of the template's model record to be used
        #message: the complete text including placeholders
        #template: the browserecord object of the template
        #context: TODO
        if message:
            logger = netsvc.Logger()
            def merge(match):
                obj_pool = self.pool.get(template.object_name.model)
                obj = obj_pool.browse(cr, uid, id)
                exp = str(match.group()[2:-2]).strip()
                #print "level 1:",exp
                exp_spl = exp.split('/')
                #print "level 2:",exp_spl
                try:
                    result = eval(exp_spl[0], {'object':obj, 'context': context,})
                except:
                    result = "Rendering Error"
                #print result
                if result in (None, False):
                    if len(exp_spl)>1:
                        return exp_spl[1]
                    else:
                        return 'Not Available'
                return str(result)
            com = re.compile('(\[\[.+?\]\])')
            message = com.sub(merge, message)
            return message

    def _on_change_ref(self,cr,uid,ids,rel_model_ref,ctx={}):
        if rel_model_ref:
            vals={}
            if ctx == {}:
                ctx = self.context
            template = self.pool.get('poweremail.templates').browse(cr,uid,ctx['active_id'],ctx)
            vals['to']= self.parsevalue(cr,uid,rel_model_ref,template.def_to,template,ctx)
            vals['cc']= self.parsevalue(cr,uid,rel_model_ref,template.def_cc,template,ctx)
            vals['bcc']= self.parsevalue(cr,uid,rel_model_ref,template.def_bcc,template,ctx)
            vals['subject']= self.parsevalue(cr,uid,rel_model_ref,template.def_subject,template,ctx)
            vals['body_text']=self.parsevalue(cr,uid,rel_model_ref,self.strip_html(template.def_body),template,ctx)
            vals['body_html']=self.parsevalue(cr,uid,rel_model_ref,template.def_body,template,ctx)
            vals['report']= self.parsevalue(cr,uid,rel_model_ref,template.file_name,template,ctx)
            #print "Vals>>>>>",vals
            return {'value':vals}
        
poweremail_preview()
class res_groups(osv.osv):
    _inherit = "res.groups"
    _description = "User Groups"
    _columns = {}
res_groups()